from dataclasses import dataclass

@dataclass
class Config:
    DATABASE_PATH: str = "instagram_sentiment.db"
    MAX_POSTS_PER_HASHTAG: int = 100
    CONFIDENCE_THRESHOLD: float = 0.6
    THEME: str = "dark"
    SUCCESS_COLOR: str = "#00CC96"
    WARNING_COLOR: str = "#FFA15A"
    ERROR_COLOR: str = "#EF553B"

config = Config()
