from collections import Counter
from datetime import datetime
import re

def color_for(sentiment: str) -> str:
    return {"Positive": "#00CC96", "Neutral": "#FFA15A", "Negative": "#EF553B"}.get(sentiment, "#FFA15A")

def orient_xticks(fig, angle=-30):
    fig.update_layout(xaxis=dict(tickangle=angle))
    return fig

def build_summary_json(df, label: str):
    total = int(len(df))
    counts = df["sentiment"].value_counts().to_dict()
    langs = df["language"].value_counts().to_dict()
    avg_conf = float(df["confidence"].mean()) if total else 0.0
    time_min = str(df["timestamp"].min()) if total else None
    time_max = str(df["timestamp"].max()) if total else None
    return {
        "label": label,
        "total_items": total,
        "sentiment_counts": counts,
        "language_counts": langs,
        "average_confidence": round(avg_conf, 3),
        "time_window": {"start": time_min, "end": time_max},
        "generated_at": datetime.now().isoformat()
    }

# Expanded stoplists: English + Hinglish + Hindi function words, add common noise tokens
EN_STOPS = {
    "a","an","the","and","or","but","if","then","else","when","while","for","with","without","to","from",
    "is","am","are","was","were","be","been","being","has","have","had","do","does","did","of","on","in","at",
    "by","as","it","its","it's","this","that","these","those","there","their","they","them","you","your","yours",
    "me","my","mine","we","our","ours","i","he","she","his","her","hers","him","us","who","whom","which","what",
    "so","very","too","much","more","most","many","few","some","any","each","every","also","just","really","like",
    "can","could","should","would","will","won't","can't","dont","didnt","isnt","wasnt","aint","u","ur","im","i'm",
    "tbh","btw","idk","ngl","fr","bro","pls","lol","lmao","omg","yh","ya","yeah","no","okay","ok","kinda","sorta",
}

HI_STOPS = {
    "है","थे","थी","हो","हूँ","हैं","में","के","को","का","की","से","पर","और","यह","वह","एक","बहुत","था","तो","भी","या","जो","क्यों","कहाँ","क्या",
    "आप","हम","तुम","मेरे","मेरा","मेरी","आपका","हमारा","यहाँ","वहाँ","कभी","सभी","कुछ","किसी","कई","कम","ज्यादा","जैसे"
}

NOISE = {"https","http","www","com","amp","rt","via","re","ve"}

EMOJI_PATTERN = re.compile(r"[\U0001F300-\U0001FAFF]")

def top_words(texts, stop_extra=None, limit=80, keep_emojis=False):
    """
    Extract top words from iterable of texts.
    - Removes URLs, mentions, and hashtags symbol while keeping the tag word.
    - Lower-cases and strips punctuation.
    - Optionally keeps emoji tokens as words.
    """
    if stop_extra is None:
        stop_extra = set()
    stops = set()
    stops |= EN_STOPS | HI_STOPS | NOISE | set(stop_extra)

    word_counts = Counter()
    for t in texts:
        s = str(t)
        # Remove URLs and mentions, detach hashtags (#tag -> tag)
        s = re.sub(r"http\S+|www\.\S+", " ", s)
        s = re.sub(r"@\w+", " ", s)
        s = re.sub(r"#(\w+)", r"\1", s)

        # Split on non-letters; capture emojis separately if desired
        tokens = []
        if keep_emojis:
            # pull out emojis as separate tokens
            emojis = EMOJI_PATTERN.findall(s)
            if emojis:
                tokens.extend(emojis)
            # remove emojis from text, continue processing
            s = EMOJI_PATTERN.sub(" ", s)

        # Normalize ASCII punctuation to spaces, lowercase
        s = s.lower()
        # Keep alphas; split
        for raw in re.split(r"[^a-z\u0900-\u097F]+", s):
            w = raw.strip()
            if not w or w in stops or len(w) <= 2:
                continue
            tokens.append(w)

        # Count
        for tok in tokens:
            # optional: skip single-emoji noise if desired (keeping for now)
            word_counts[tok] += 1

    return dict(word_counts.most_common(limit))
