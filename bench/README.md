# Benchmarks (Jammy)

## STT on Hinglish (`stt_bench.py`, task T0.3)

Scores faster-whisper on five corpus lines read aloud. The reference text is the corpus line itself
(`stt_clips.json` points at corpus id and turn), so there is nothing to transcribe by hand.

Reported per model and language mode:
- **WER / CER** after lowercasing and stripping punctuation (UPI IDs and links stay one token).
- **ms per audio second**: decode compute divided by clip length (ms of compute per second of audio). Below 1000 means faster than real time.
- **deva**: share of output letters in Devanagari. The reference is Roman-script, so a high value makes WER meaningless.
- **intel**: identifiers the extraction engine finds in the reference vs. in the transcript. This is what the
  product depends on.

### Record the clips
1. Read each line from `stt_clips.json` (the corpus turn it names) at a normal phone-call pace. Use a human voice;
   synthetic voices are only good for a smoke test.
2. Save as `bench/clips/01_threat.wav` and so on. Any format ffmpeg reads is fine for the benchmark. For the replay source
   (`WavFileSource`), convert to 16 kHz mono PCM16: `ffmpeg -i in.m4a -ar 16000 -ac 1 -sample_fmt s16 out.wav`.
3. `bench/clips/` and `bench/results/` are gitignored. Never commit audio.

### Run
```
pip install faster-whisper
python bench/stt_bench.py --label "human, laptop mic"                       # base,small x hi,en on CPU int8
python bench/stt_bench.py --models small,distil-large-v3 --device cuda --compute float16 --label "demo GPU"
```
Each run writes the full log (every reference, transcript and timing) to `bench/results/stt_<timestamp>.json`.
Numbers quoted anywhere public come from a logged run on the demo machine, with the label saying what was measured.

## Models (local, gitignored under `models/`)
- Silero VAD: `pip install silero-vad --no-deps` (ships the ONNX file; torch is not needed), or put
  `silero_vad.onnx` in `models/`.
- Piper Hindi voice (default `hi_IN-rohan-medium`): download `hi_IN-rohan-medium.onnx` and `.onnx.json` from
  `huggingface.co/rhasspy/piper-voices` (path `hi/hi_IN/rohan/medium/`) into `models/piper/`.
