from pydantic import BaseModel
from typing import Optional


class Article(BaseModel):
    title: str
    url: str
    source: str
    published: Optional[str] = None
    snippet: Optional[str] = None


class NewsEvent(BaseModel):
    topic: str
    headline: str
    summary: str
    sources: list[Article]
    sources_count: int
    verified: bool  # True se confermato da >= MIN_SOURCES_FOR_VERIFIED fonti


class TopicNewsResponse(BaseModel):
    topic: str
    events: list[NewsEvent]
    fetched_at: str
