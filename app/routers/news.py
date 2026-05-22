from fastapi import APIRouter, HTTPException, Query
from ..services.news_engine import get_news_for_topic, get_news_for_topics
from ..services.feeds import get_available_topics
from ..models.news import TopicNewsResponse

router = APIRouter(prefix="/api/v1", tags=["news"])


@router.get("/topics")
async def list_topics() -> dict:
    """Ritorna i topic disponibili."""
    return {"topics": get_available_topics()}


@router.get("/news/{topic}", response_model=TopicNewsResponse)
async def get_topic_news(topic: str) -> TopicNewsResponse:
    """Notizie verificate per un singolo topic."""
    available = get_available_topics()
    if topic.lower() not in available:
        raise HTTPException(
            status_code=404,
            detail=f"Topic '{topic}' non disponibile. Disponibili: {available}",
        )
    return await get_news_for_topic(topic)


@router.get("/news", response_model=list[TopicNewsResponse])
async def get_multi_topic_news(
    topics: list[str] = Query(..., description="Lista topic, es. ?topics=tecnologia&topics=economia")
) -> list[TopicNewsResponse]:
    """Notizie per più topic in parallelo."""
    available = get_available_topics()
    invalid = [t for t in topics if t.lower() not in available]
    if invalid:
        raise HTTPException(
            status_code=400,
            detail=f"Topic non validi: {invalid}. Disponibili: {available}",
        )
    return await get_news_for_topics(topics)
