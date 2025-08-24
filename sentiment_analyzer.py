import re
from textblob import TextBlob
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer

try:
    from googletrans import Translator
    _translator = Translator()
except Exception:
    _translator = None

vader = SentimentIntensityAnalyzer()

def detect_language(text: str) -> str:
    return "hi" if re.search(r"[\u0900-\u097F]", text) else "en"

def clean_text(text: str) -> str:
    t = re.sub(r"http\S+|www\S+", "", text)
    t = re.sub(r"@\w+", "", t)
    t = re.sub(r"#(\w+)", r"\1", t)
    t = " ".join(t.split())
    return t

def maybe_translate_to_en(text: str, lang: str):
    if lang == "en" or not _translator:
        return None
    try:
        res = _translator.translate(text, src="auto", dest="en")
        return res.text
    except Exception:
        return None

def analyze_text(text: str):
    original = text
    t = clean_text(original)
    lang = detect_language(t)

    translated = maybe_translate_to_en(t, lang)
    t_en = translated if translated else t

    vs = vader.polarity_scores(t_en)
    vader_label = "Positive" if vs["compound"] >= 0.05 else "Negative" if vs["compound"] <= -0.05 else "Neutral"

    tb = TextBlob(t_en)
    tb_pol = tb.sentiment.polarity
    tb_label = "Positive" if tb_pol > 0.1 else "Negative" if tb_pol < -0.1 else "Neutral"

    if vader_label == tb_label:
        final = vader_label
    else:
        final = vader_label if abs(vs["compound"]) >= abs(tb_pol) else tb_label

    conf = (abs(vs["compound"]) + abs(tb_pol)) / 2
    return {
        "sentiment": final,
        "confidence": round(conf, 3),
        "vader_compound": vs["compound"],
        "textblob_polarity": tb_pol,
        "language": lang,
        "clean_text": t,
        "translated_text": translated,
        "used_translation": translated is not None,
    }

def batch_analyze(items):
    results = []
    for it in items:
        res = analyze_text(it["text"])
        results.append({**it, **res})
    return results
