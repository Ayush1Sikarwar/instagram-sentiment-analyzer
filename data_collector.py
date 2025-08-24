from datetime import datetime, timedelta
import random
import re
from typing import List, Tuple

# Accepts www., m., or no subdomain; path can be /p/, /reel/, /tv/, followed by a shortcode (>=5 chars), with optional extra path/query
SHORTCODE_RE = re.compile(
    r"^(?:https?://)?(?:www\.|m\.)?instagram\.com/(?:p|reel|tv)/([A-Za-z0-9_-]{5,})(?:[/?].*)?$",
    re.IGNORECASE
)

# Scale knobs for how much synthetic data to generate
MIN_COMMENTS_PER_POST = 40
MAX_COMMENTS_PER_POST = 120   # raise this to get more items per post

# Varied comment generator (Hinglish + emojis + intensifiers)
POS_PHRASES = ["love this", "amazing", "awesome", "so good", "fantastic", "beautiful", "lit", "fire", "mast", "bahut badhiya"]
NEG_PHRASES = ["not good", "terrible", "bad", "disappointing", "overrated", "waste", "boring", "meh", "pasand nahi aaya", "bakwaas"]
NEU_PHRASES = ["okay", "fine", "decent", "interesting", "nice", "theek hai", "cool", "hm", "fair", "works"]

EMOJIS_POS = ["😍", "🔥", "✨", "🥰", "👏", "💯", "🙌"]
EMOJIS_NEG = ["😞", "😒", "😡", "👎", "🤦", "🥲"]
EMOJIS_NEU = ["🙂", "🤔", "😐", "🫡"]

HINGLISH_FILLERS = ["yrr", "btw", "lol", "fr", "tbh", "ik", "bro", "pls", "na", "bc", "ngl"]
INTENSIFIERS = ["really", "truly", "seriously", "kinda", "pretty", "very", "bahut", "zyada"]

def _rand(seq): return random.choice(seq)
def _maybe(seq, p=0.5): return _rand(seq) if random.random() < p else ""

def _make_comment(sent: str) -> str:
    parts = []
    if random.random() < 0.5: parts.append(_maybe(HINGLISH_FILLERS, 0.6))
    if random.random() < 0.5: parts.append(_maybe(INTENSIFIERS, 0.7))
    parts.append(sent)
    if random.random() < 0.6:
        if sent in POS_PHRASES: parts.append(_maybe(EMOJIS_POS, 0.9))
        elif sent in NEG_PHRASES: parts.append(_maybe(EMOJIS_NEG, 0.9))
        else: parts.append(_maybe(EMOJIS_NEU, 0.7))
    return " ".join([x for x in parts if x]).strip()

def _random_comment_text() -> str:
    r = random.random()
    if r < 0.4: base = _rand(POS_PHRASES)
    elif r < 0.7: base = _rand(NEU_PHRASES)
    else: base = _rand(NEG_PHRASES)
    return _make_comment(base)

class InstagramDataCollector:
    def __init__(self):
        # Expanded popular hashtags with sample captions
        self.sample = {
            "food": [
                "यह restaurant का खाना बहुत स्वादिष्ट है! 😋 Highly recommended!",
                "Amazing pasta at this Italian place! Worth every penny 🍝",
                "Disappointed with the service. Food was cold when served 😞",
                "मुझे यह pizza बिल्कुल पसंद नहीं आया। Very expensive for the quality.",
                "Best biryani in the city! आज तक का सबसे अच्छा खाना! 🍛",
                "Fresh ingredients, authentic taste. Loved the experience! 👌",
            ],
            "travel": [
                "Incredible sunset at Marina Bay! 🌅",
                "गोवा के beaches पर amazing time बिताया! 🏖️",
                "Flight delayed by 3 hours. Terrible start 😤",
                "Manali का weather बहुत सुंदर है! 🏔️",
                "Hotel was dirty and overpriced. Worst travel experience.",
                "Kerala backwaters are breathtaking! Must visit 🛶",
            ],
            "movie": [
                "Just watched the new film — absolutely fantastic! 🎬",
                "यह movie बहुत अच्छी थी, acting कमाल की!",
                "Predictable plot and weak dialogues, disappointed.",
                "Soundtrack was amazing and elevated the film 🎵",
                "Lengthy but worth it for the climax.",
            ],
            "fashion": [
                "New drop is clean and classy! ✨",
                "Overpriced but looks premium ngl.",
                "Stitching could be better, threads showing.",
                "Perfect festive vibes — mast outfit!",
                "Colors pop nicely in daylight.",
            ],
            "technology": [
                "Battery life is insane — easily 2 days! 🔋",
                "Heating issue after long gaming sessions.",
                "Camera is crisp even in low light.",
                "UI feels smooth and responsive.",
                "Price is a bit too high for specs.",
            ],
            "sports": [
                "What a clutch performance! 🏆",
                "Defense was asleep today fr.",
                "Captain leading from the front — respect.",
                "Ref decisions were questionable ngl.",
                "Team chemistry looking better each game.",
            ],
            "music": [
                "Hook is stuck in my head already 🎵",
                "Lyrics could've been deeper.",
                "Beat drop is crazy — dance floor ready!",
                "Mix feels muddy on earphones.",
                "Vocals sit perfectly in the mix.",
            ],
            "gaming": [
                "New update is OP! 🔥",
                "Nerfs ruined my main character :(",
                "Matchmaking feels more balanced now.",
                "Server lag is still annoying.",
                "Graphics look stunning on high.",
            ],
            "fitness": [
                "Form > ego lifting always.",
                "PR day — felt unstoppable today! 💪",
                "Recovery matters more than people think.",
                "Knees felt weird on squats, deload time.",
                "Great pump with simple movements.",
            ],
            "news": [
                "Finally some positive developments.",
                "Feels like the same story again.",
                "Hope this actually leads to action.",
                "Mixed responses across regions.",
                "People deserve better transparency.",
            ],
            "education": [
                "This resource explains concepts so clearly.",
                "Assignments back-to-back — burnout is real.",
                "Group study session helped a lot!",
                "Exam dates announced — time to lock in.",
                "Wish we had more hands-on labs.",
            ],
            "health": [
                "Hydration and sleep changed everything.",
                "Stress management needs way more focus.",
                "Small steps daily > big unsustainable changes.",
                "Appointment system still confusing tbh.",
                "Glad to see awareness increasing.",
            ],
        }

    def get_available_hashtags(self):
        return list(self.sample.keys())

    def _fake_comments(self, post_id: str, hashtag: str, count: int):
        now = datetime.now()
        out = []
        for i in range(count):
            out.append({
                "post_id": post_id,
                "comment_id": f"{post_id}_c{i+1:04d}",
                "hashtag": hashtag,
                "text": _random_comment_text(),
                "author_username": f"cuser_{random.randint(100,999)}",
                "likes_count": random.randint(0, 60),
                "timestamp": now - timedelta(minutes=random.randint(1, 60*24)),
                "type": "comment",
            })
        return out

    def collect_hashtag_data(self, hashtag: str, max_posts: int = 50, include_comments: bool = True) -> Tuple[list, list]:
        """Return up to max_posts captions from the hashtag sample and lots of comments per caption."""
        texts = self.sample.get(hashtag.lower(), [])
        posts = []
        now = datetime.now()

        # Repeat/loop the sample to reach requested max_posts if needed
        if not texts:
            texts = ["No sample text available."]
        expanded = []
        while len(expanded) < max_posts:
            expanded.extend(texts)
        expanded = expanded[:max_posts]

        for i, text in enumerate(expanded):
            pid = f"{hashtag}_{i+1:04d}"
            posts.append({
                "post_id": pid,
                "hashtag": hashtag,
                "text": text,
                "author_username": f"user_{random.randint(1000,9999)}",
                "likes_count": random.randint(0, 1000),
                "timestamp": now - timedelta(hours=random.randint(1,72)),
                "type": "caption",
            })

        comments = []
        if include_comments:
            for p in posts:
                n = random.randint(MIN_COMMENTS_PER_POST, MAX_COMMENTS_PER_POST)
                comments.extend(self._fake_comments(p["post_id"], hashtag, count=n))
        return posts, comments

    def extract_shortcode(self, url: str) -> str | None:
        u = url.strip()
        # Unwrap l.instagram.com redirect links
        if "l.instagram.com" in u and "u=" in u:
            try:
                from urllib.parse import urlparse, parse_qs, unquote
                qs = parse_qs(urlparse(u).query)
                real = unquote(qs.get("u", [""])[0])
                if real:
                    u = real
            except Exception:
                pass
        m = SHORTCODE_RE.match(u)
        return m.group(1) if m else None

    def _fake_caption_for_shortcode(self, shortcode: str) -> str:
        caps = [
            "Beautiful day at the beach! 🌊☀️",
            "यह dish लाजवाब है — must try! 😋",
            "Long day but grateful for these small wins 🙏",
            "New setup is clean and minimal. Thoughts?",
            "Mixed feelings about this update, क्या सोचते हो?",
            "Sunset view never disappoints 🌅",
        ]
        return caps[abs(hash(shortcode)) % len(caps)]

    def collect_from_urls(self, urls: List[str], include_comments: bool = True) -> Tuple[list, list]:
        posts, comments = [], []
        now = datetime.now()
        for u in urls:
            code = self.extract_shortcode(u)
            if not code:
                continue
            caption = self._fake_caption_for_shortcode(code)  # Replace with real fetch if you add auth/scraping
            post = {
                "post_id": f"url_{code}",
                "hashtag": "url_mode",
                "text": caption,
                "author_username": f"user_{random.randint(1000,9999)}",
                "likes_count": random.randint(0, 5000),
                "timestamp": now - timedelta(hours=random.randint(1, 72)),
                "type": "caption",
                "source_url": u.strip(),
            }
            posts.append(post)
            if include_comments:
                n = random.randint(MIN_COMMENTS_PER_POST, MAX_COMMENTS_PER_POST)
                comments.extend(self._fake_comments(post["post_id"], "url_mode", count=n))
        return posts, comments

    def build_from_pasted_comments(self, lines: List[str]) -> Tuple[list, list]:
        now = datetime.now()
        comments = []
        for i, t in enumerate([ln for ln in lines if ln.strip()]):
            comments.append({
                "post_id": f"pasted_{i//200}",  # group more densely to scale
                "comment_id": f"p_{i+1:05d}",
                "hashtag": "pasted",
                "text": t.strip(),
                "author_username": f"u_{1000+i}",
                "likes_count": random.randint(0, 30),
                "timestamp": now - timedelta(minutes=random.randint(1, 60*24)),
                "type": "comment",
            })
        return [], comments

data_collector = InstagramDataCollector()
