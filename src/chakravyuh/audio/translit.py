# Engineered by uncoalesced
"""Roman Hinglish -> Devanagari for the Hindi Piper voices, which read Roman text with English phonemes.
The core stays Roman-script (docs/CONTRACTS.md); this runs just before TTS.

A lexicon covers the persona's vocabulary and common English loanwords; anything else goes through spelling rules
(greedy longest match, word-final "a" read as aa). Output only has to be pronounceable, not dictionary-correct.
ponytail: rules mangle unlisted English words ("screen" -> स्क्रीन only because it is listed). Grow LEXICON from
real LLM output; if that stops scaling, have the LLM emit Devanagari alongside Roman (contract change, ask Joel)."""
import re

LEXICON = {
    # persona vocabulary (fsm.LINES["hi"]) and common Hinglish
    "aa": "आ", "aadmi": "आदमी", "aap": "आप", "aapka": "आपका", "aapki": "आपकी", "aapke": "आपके", "aapse": "आपसे",
    "aawaaz": "आवाज़", "aaya": "आया", "ab": "अब", "abhi": "अभी", "acha": "अच्छा", "accha": "अच्छा", "achha": "अच्छा",
    "akshar": "अक्षर", "aisa": "ऐसा", "arre": "अरे", "aur": "और", "baap": "बाप", "baar": "बार", "baat": "बात",
    "bahut": "बहुत", "bas": "बस", "bata": "बता", "bataiye": "बताइए", "batao": "बताओ", "beta": "बेटा",
    "bhai": "भाई", "bhejna": "भेजना", "bhejta": "भेजता", "bhej": "भेज", "bimaar": "बीमार", "bol": "बोल",
    "boliye": "बोलिए", "budha": "बूढ़ा", "chahta": "चाहता", "chashma": "चश्मा", "chhoti": "छोटी", "deta": "देता",
    "dheere": "धीरे", "dhoondhne": "ढूँढने", "dijiye": "दीजिए", "dikha": "दिखा", "dikhta": "दिखता", "do": "दो",
    "dohra": "दोहरा", "ek": "एक", "ghar": "घर", "ghoom": "घूम", "hai": "है", "hain": "हैं", "haan": "हाँ",
    "ho": "हो", "hoon": "हूँ", "hun": "हूँ", "jee": "जी", "ji": "जी", "jeeta": "जीता", "jo": "जो", "kaan": "कान",
    "kam": "कम", "karke": "करके", "karna": "करना", "karta": "करता", "karun": "करूँ", "kar": "कर", "kat": "कट",
    "kaunsa": "कौनसा", "ki": "की", "ka": "का", "ke": "के", "kijiye": "कीजिए", "kis": "किस", "koi": "कोई",
    "kuch": "कुछ", "kya": "क्या", "leta": "लेता", "likh": "लिख", "likha": "लिखा", "main": "मैं", "mai": "मैं",
    "mat": "मत", "mera": "मेरा", "meri": "मेरी", "mere": "मेरे", "mil": "मिल", "mujhe": "मुझे", "na": "ना",
    "naam": "नाम", "nahi": "नहीं", "nahin": "नहीं", "paisa": "पैसा", "paise": "पैसे", "par": "पर",
    "patni": "पत्नी", "pe": "पे", "phir": "फिर", "pooch": "पूछ", "poori": "पूरी", "raha": "रहा", "rahi": "रही",
    "rahe": "रहे", "re": "रे", "ruko": "रुको", "saaf": "साफ़", "sahab": "साहब", "saab": "साब", "se": "से",
    "sirf": "सिर्फ़", "sunta": "सुनता", "suniye": "सुनिए", "theek": "ठीक", "thik": "ठीक", "to": "तो", "toh": "तो",
    "wahi": "वही", "wo": "वो", "woh": "वो", "ya": "या", "ye": "ये", "yeh": "ये", "zara": "ज़रा", "zor": "ज़ोर",
    "hum": "हम", "tum": "तुम", "kab": "कब", "kahan": "कहाँ", "kaise": "कैसे", "kyun": "क्यों", "kyon": "क्यों",
    "sab": "सब", "samajh": "समझ", "ruk": "रुक", "jaldi": "जल्दी", "dhanyavaad": "धन्यवाद",
    "raghunath": "रघुनाथ",
    # English loanwords as Hindi speakers say them
    "account": "अकाउंट", "app": "ऐप", "bill": "बिल", "bot": "बॉट", "code": "कोड", "detail": "डिटेल",
    "details": "डिटेल्स", "error": "एरर", "exceed": "एक्सीड", "fail": "फ़ेल", "hello": "हेलो", "hi": "हाय",
    "id": "आईडी", "ifsc": "आईएफ़एससी", "internet": "इंटरनेट", "limit": "लिमिट", "minute": "मिनट",
    "number": "नंबर", "ok": "ओके", "okay": "ओके", "payment": "पेमेंट", "pen": "पेन", "pension": "पेंशन",
    "phone": "फ़ोन", "please": "प्लीज़", "retired": "रिटायर्ड", "screen": "स्क्रीन", "sir": "सर",
    "teacher": "टीचर", "try": "ट्राई", "upi": "यूपीआई", "bank": "बैंक", "otp": "ओटीपी", "son": "सन",
    "second": "सेकंड", "sorry": "सॉरी", "thank": "थैंक", "you": "यू", "line": "लाइन", "network": "नेटवर्क",
}

_CONS = {"chh": "छ", "kh": "ख", "gh": "घ", "ch": "च", "jh": "झ", "th": "थ", "dh": "ध", "ph": "फ", "bh": "भ",
         "sh": "श", "k": "क", "g": "ग", "j": "ज", "t": "त", "d": "द", "n": "न", "p": "प", "b": "ब", "m": "म",
         "y": "य", "r": "र", "l": "ल", "v": "व", "w": "व", "s": "स", "h": "ह", "f": "फ़", "z": "ज़", "q": "क",
         "c": "क", "x": "क्स"}
_VOW = {"aa": ("आ", "ा"), "ai": ("ऐ", "ै"), "au": ("औ", "ौ"), "ee": ("ई", "ी"), "ii": ("ई", "ी"),
        "oo": ("ऊ", "ू"), "uu": ("ऊ", "ू"), "a": ("अ", ""), "i": ("इ", "ि"), "u": ("उ", "ु"), "e": ("ए", "े"),
        "o": ("ओ", "ो")}
_TOKEN = re.compile("|".join(sorted(map(re.escape, [*_CONS, *_VOW]), key=len, reverse=True)))
_VIRAMA = "्"
_WORD = re.compile(r"[A-Za-z]+")


def _rules(word: str) -> str:
    parts = _TOKEN.findall(word.lower())
    out, prev_cons = [], False
    for i, p in enumerate(parts):
        last = i == len(parts) - 1
        if p in _VOW:
            full, matra = _VOW[p]
            if p == "a" and last and prev_cons and len(parts) > 2:
                matra = "ा"                           # Hinglish word-final -a is long: raha, mera, kya
            out.append(matra if prev_cons else full)
            prev_cons = False
        else:
            if prev_cons:
                out.append(_VIRAMA)
            out.append(_CONS[p])
            prev_cons = True
    return "".join(out)


def to_devanagari(text: str) -> str:
    return _WORD.sub(lambda m: LEXICON.get(m.group().lower()) or _rules(m.group()), text)
