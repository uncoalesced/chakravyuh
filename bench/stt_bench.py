# Engineered by uncoalesced
"""STT benchmark on Hinglish clips (T0.3). For each model x language it logs WER, CER, real-time factor, milliseconds
of compute per second of audio, how much of the output is Devanagari, and intel recall: the share of identifiers
(UPI, phone, account, IFSC) in the reference that the extraction engine still finds in the transcript. Intel recall is
the number that matters for the product; WER is reported because the task asks for it.

    python bench/stt_bench.py                                  # defaults: base,small x hi,en
    python bench/stt_bench.py --models small --langs en,auto --device cuda --compute float16

Needs `pip install faster-whisper`. Writes a JSON log to bench/results/ (gitignored)."""
import argparse
import json
import pathlib
import platform
import re
import sys
import time
from datetime import datetime

ROOT = pathlib.Path(__file__).parent.parent
sys.path.insert(0, str(ROOT / "src"))
from chakravyuh.extract import extract  # noqa: E402

BENCH = pathlib.Path(__file__).parent
_PUNCT = re.compile(r"[^\w\s@.]|(?<!\w)[.@]|[.@](?!\w)")
_DEVA = re.compile(r"[ऀ-ॿ]")


def normalise(text: str) -> list:
    """Lowercase, drop punctuation but keep '@' and '.' inside tokens (UPI IDs, links). Returns words."""
    return _PUNCT.sub(" ", text.lower()).split()


def edit_distance(a, b) -> int:
    prev = list(range(len(b) + 1))
    for i, x in enumerate(a, 1):
        cur = [i]
        for j, y in enumerate(b, 1):
            cur.append(min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + (x != y)))
        prev = cur
    return prev[-1]


def wer(ref: str, hyp: str) -> float:
    r = normalise(ref)
    return edit_distance(r, normalise(hyp)) / max(len(r), 1)


def cer(ref: str, hyp: str) -> float:
    r, h = " ".join(normalise(ref)), " ".join(normalise(hyp))
    return edit_distance(r, h) / max(len(r), 1)


def devanagari_share(text: str) -> float:
    letters = [c for c in text if c.isalpha()]
    return sum(bool(_DEVA.match(c)) for c in letters) / max(len(letters), 1)


def intel_recall(ref: str, hyp: str):
    """(found, expected) over identifiers extracted from the reference. None expected -> (0, 0)."""
    want = {(i.kind, i.value) for i in extract(ref)}
    got = {(i.kind, i.value) for i in extract(hyp)}
    return len(want & got), len(want)


def load_clips(manifest: pathlib.Path):
    spec = json.loads(manifest.read_text(encoding="utf-8"))
    for c in spec["clips"]:
        ref = c.get("ref") or json.loads((ROOT / "corpus" / f"{c['corpus']}.json").read_text(encoding="utf-8"))["turns"][c["turn"]]["text"]
        yield manifest.parent / c["file"], ref


def run(models, langs, clips, device, compute, beam):
    from faster_whisper import WhisperModel
    rows = []
    for name in models:
        t0 = time.perf_counter()
        model = WhisperModel(name, device=device, compute_type=compute)
        load_s = time.perf_counter() - t0
        list(model.transcribe(str(clips[0][0]), beam_size=beam)[0])           # warm-up, not timed
        for lang in langs:
            for path, ref in clips:
                t0 = time.perf_counter()
                segs, info = model.transcribe(str(path), language=None if lang == "auto" else lang,
                                              beam_size=beam, vad_filter=False, condition_on_previous_text=False)
                hyp = " ".join(s.text.strip() for s in segs)          # segments are lazy; this runs the decode
                took = time.perf_counter() - t0
                found, expected = intel_recall(ref, hyp)
                rows.append({"model": name, "lang": lang, "clip": path.name, "audio_s": round(info.duration, 2),
                             "compute_s": round(took, 3), "rtf": round(took / info.duration, 3),
                             "ms_per_audio_s": round(1000 * took / info.duration, 1),
                             "wer": round(wer(ref, hyp), 3), "cer": round(cer(ref, hyp), 3),
                             "devanagari": round(devanagari_share(hyp), 2), "detected_lang": info.language,
                             "intel_found": found, "intel_expected": expected, "ref": ref, "hyp": hyp,
                             "model_load_s": round(load_s, 2)})
                print(f"{name:>8} {lang:>4} {path.name:<18} wer={rows[-1]['wer']:.2f} cer={rows[-1]['cer']:.2f} "
                      f"rtf={rows[-1]['rtf']:.2f} intel={found}/{expected}  | {hyp[:70]}")
    return rows


def summarise(rows):
    out = []
    for key in sorted({(r["model"], r["lang"]) for r in rows}):
        g = [r for r in rows if (r["model"], r["lang"]) == key]
        audio = sum(r["audio_s"] for r in g)
        found, expected = sum(r["intel_found"] for r in g), sum(r["intel_expected"] for r in g)
        out.append({"model": key[0], "lang": key[1], "clips": len(g),
                    "wer": round(sum(r["wer"] for r in g) / len(g), 3),
                    "cer": round(sum(r["cer"] for r in g) / len(g), 3),
                    "ms_per_audio_s": round(1000 * sum(r["compute_s"] for r in g) / audio, 1),
                    "devanagari": round(sum(r["devanagari"] for r in g) / len(g), 2),
                    "intel_recall": f"{found}/{expected}"})
    return out


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--models", default="base,small", help="comma list, e.g. base,small,distil-large-v3")
    ap.add_argument("--langs", default="hi,en", help="comma list of whisper language codes, or 'auto'")
    ap.add_argument("--manifest", default=str(BENCH / "stt_clips.json"))
    ap.add_argument("--device", default="auto")
    ap.add_argument("--compute", default="int8", help="int8 on CPU, float16 on GPU")
    ap.add_argument("--beam", type=int, default=1, help="1 = greedy, closest to live use")
    ap.add_argument("--label", default="", help="free text stored in the log, e.g. 'human voice, laptop mic'")
    a = ap.parse_args(argv)

    clips = list(load_clips(pathlib.Path(a.manifest)))
    missing = [str(p) for p, _ in clips if not p.exists()]
    if missing:
        sys.exit("missing clips (record them first, see bench/README.md):\n  " + "\n  ".join(missing))

    rows = run(a.models.split(","), a.langs.split(","), clips, a.device, a.compute, a.beam)
    summary = summarise(rows)
    print(f"\n{'model':>8} {'lang':>4} {'WER':>6} {'CER':>6} {'ms/s':>7} {'deva':>5} intel")
    for s in summary:
        print(f"{s['model']:>8} {s['lang']:>4} {s['wer']:>6.2f} {s['cer']:>6.2f} {s['ms_per_audio_s']:>7.0f} "
              f"{s['devanagari']:>5.2f} {s['intel_recall']}")

    out = BENCH / "results" / f"stt_{datetime.now():%Y%m%d_%H%M%S}.json"
    out.parent.mkdir(exist_ok=True)
    out.write_text(json.dumps({"label": a.label, "machine": platform.processor() or platform.machine(),
                               "device": a.device, "compute": a.compute, "beam": a.beam,
                               "summary": summary, "rows": rows}, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"\nlog: {out.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
