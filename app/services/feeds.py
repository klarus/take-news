import feedparser
import httpx
import asyncio
from datetime import datetime, timezone, timedelta
from email.utils import parsedate_to_datetime
from ..models.news import Article

MAX_AGE = timedelta(days=2)


def _parse_date(date_str: str) -> datetime | None:
    if not date_str:
        return None
    for parser in (parsedate_to_datetime, lambda s: datetime.fromisoformat(s)):
        try:
            dt = parser(date_str)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            return dt
        except Exception:
            continue
    return None


def _is_recent(date_str: str) -> bool:
    dt = _parse_date(date_str)
    if dt is None:
        return True  # data non parsabile → includi per sicurezza
    return datetime.now(timezone.utc) - dt <= MAX_AGE

# RSS feeds per topic — aggiungere/rimuovere liberamente
TOPIC_FEEDS: dict[str, list[str]] = {
    "tecnologia": [
        "https://feeds.feedburner.com/TechCrunch",
        "https://www.wired.com/feed/rss",
        "https://feeds.arstechnica.com/arstechnica/index",
        "https://www.theverge.com/rss/index.xml",
        "https://rss.nytimes.com/services/xml/rss/nyt/Technology.xml",
        "https://feeds.bbci.co.uk/news/technology/rss.xml",
    ],
    "politica": [
        "https://rss.nytimes.com/services/xml/rss/nyt/Politics.xml",
        "https://feeds.bbci.co.uk/news/politics/rss.xml",
        "https://www.theguardian.com/politics/rss",
        "https://feeds.reuters.com/reuters/politicsNews",
        "https://rss.dw.com/rdf/rss-it-pol",
        "https://www.corriere.it/rss/politica.xml",
    ],
    "economia": [
        "https://feeds.reuters.com/reuters/businessNews",
        "https://feeds.bloomberg.com/markets/news.rss",
        "https://www.ft.com/rss/home",
        "https://rss.nytimes.com/services/xml/rss/nyt/Business.xml",
        "https://feeds.bbci.co.uk/news/business/rss.xml",
        "https://www.corriere.it/rss/economia.xml",
    ],
    "scienza": [
        "https://feeds.bbci.co.uk/news/science_and_environment/rss.xml",
        "https://www.sciencedaily.com/rss/all.xml",
        "https://rss.nytimes.com/services/xml/rss/nyt/Science.xml",
        "https://feeds.nature.com/nature/rss/current",
        "https://www.newscientist.com/feed/home/",
        "https://feeds.feedburner.com/nasa/breaking",
    ],
    "sport": [
        "https://feeds.bbci.co.uk/sport/rss.xml",
        "https://www.espn.com/espn/rss/news",
        "https://rss.nytimes.com/services/xml/rss/nyt/Sports.xml",
        "https://www.gazzetta.it/rss/home.xml",
        "https://www.corrieredellosport.it/rss",
        "https://feeds.reuters.com/reuters/sportsNews",
    ],
    "salute": [
        "https://feeds.bbci.co.uk/news/health/rss.xml",
        "https://rss.nytimes.com/services/xml/rss/nyt/Health.xml",
        "https://www.who.int/rss-feeds/news-releases-rss.xml",
        "https://feeds.feedburner.com/MedscapeGeneralMedicineHeadlines",
        "https://www.medicalnewstoday.com/rss",
        "https://www.corriere.it/rss/salute.xml",
    ],
    "mondo": [
        "https://feeds.bbci.co.uk/news/world/rss.xml",
        "https://feeds.reuters.com/reuters/worldNews",
        "https://rss.nytimes.com/services/xml/rss/nyt/World.xml",
        "https://www.theguardian.com/world/rss",
        "https://rss.dw.com/rdf/rss-it-all",
        "https://www.aljazeera.com/xml/rss/all.xml",
    ],
    "italia": [
        "https://www.corriere.it/rss/homepage.xml",
        "https://www.repubblica.it/rss/homepage/rss2.0.xml",
        "https://www.ansa.it/sito/notizie/cronaca/cronaca_rss.xml",
        "https://feeds.bbci.co.uk/news/world/europe/rss.xml",
        "https://rss.dw.com/rdf/rss-it-all",
        "https://www.lastampa.it/rss",
    ],
}

HEADERS = {"User-Agent": "NewsSynth/1.0 (news aggregator app)"}


async def fetch_feed(client: httpx.AsyncClient, url: str, source_name: str) -> list[Article]:
    try:
        resp = await client.get(url, timeout=10.0, follow_redirects=True)
        resp.raise_for_status()
        feed = feedparser.parse(resp.text)
        articles = []
        for entry in feed.entries[:15]:
            pub = entry.get("published", entry.get("updated", ""))
            if not _is_recent(pub):
                continue
            articles.append(Article(
                title=entry.get("title", "").strip(),
                url=entry.get("link", ""),
                source=source_name,
                published=pub,
                snippet=(entry.get("summary", "") or "")[:300].strip(),
            ))
        return articles
    except Exception:
        return []


def _source_name(url: str) -> str:
    try:
        from urllib.parse import urlparse
        host = urlparse(url).netloc
        return host.replace("www.", "").replace("feeds.", "").split(".")[0].title()
    except Exception:
        return url


async def fetch_articles_for_topic(topic: str) -> list[Article]:
    topic_key = topic.lower()
    feeds = TOPIC_FEEDS.get(topic_key, TOPIC_FEEDS.get("mondo", []))

    async with httpx.AsyncClient(headers=HEADERS) as client:
        tasks = [fetch_feed(client, url, _source_name(url)) for url in feeds]
        results = await asyncio.gather(*tasks)

    articles: list[Article] = []
    for batch in results:
        articles.extend(batch)
    return articles


def get_available_topics() -> list[str]:
    return sorted(TOPIC_FEEDS.keys())
