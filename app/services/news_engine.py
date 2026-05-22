"""
Orchestratore: fetch → cluster → verifica → sintesi AI → response
"""
import asyncio
import os
from datetime import datetime, timezone
from cachetools import TTLCache

from .feeds import fetch_articles_for_topic
from .clustering import cluster_articles
from .ai_summarizer import summarize_event
from ..models.news import NewsEvent, TopicNewsResponse

MIN_SOURCES = int(os.getenv("MIN_SOURCES_FOR_VERIFIED", "5"))
CACHE_TTL = int(os.getenv("CACHE_TTL_MINUTES", "30")) * 60
MAX_EVENTS_PER_TOPIC = 8

_cache: TTLCache = TTLCache(maxsize=50, ttl=CACHE_TTL)


async def get_news_for_topic(topic: str) -> TopicNewsResponse:
    topic_key = topic.lower().strip()
    if topic_key in _cache:
        return _cache[topic_key]

    articles = await fetch_articles_for_topic(topic_key)
    clusters = cluster_articles(articles)

    # Considera solo cluster con almeno 2 fonti diverse
    clusters = [
        c for c in clusters
        if len({a.source for a in c}) >= 2
    ][:MAX_EVENTS_PER_TOPIC]

    # Sintesi AI sequenziale per rispettare il rate limit Gemini free tier
    summaries = []
    for cluster in clusters:
        result = await summarize_event(topic_key, cluster)
        summaries.append(result)

    events: list[NewsEvent] = []
    for cluster, (headline, summary) in zip(clusters, summaries):
        unique_sources = {a.source for a in cluster}
        events.append(NewsEvent(
            topic=topic_key,
            headline=headline,
            summary=summary,
            sources=cluster,
            sources_count=len(unique_sources),
            verified=len(unique_sources) >= MIN_SOURCES,
        ))

    result = TopicNewsResponse(
        topic=topic_key,
        events=events,
        fetched_at=datetime.now(timezone.utc).isoformat(),
    )
    _cache[topic_key] = result
    return result


async def get_news_for_topics(topics: list[str]) -> list[TopicNewsResponse]:
    return await asyncio.gather(*[get_news_for_topic(t) for t in topics])
