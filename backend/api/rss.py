"""
RSS Feed API Endpoints
Exposes ingested RSS news articles for frontend consumption
"""

from fastapi import APIRouter, Query
from typing import List, Optional
from pydantic import BaseModel
from datetime import datetime
import json
from pathlib import Path
import structlog

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/api/rss", tags=["rss"])


class NewsArticle(BaseModel):
    """News article from RSS feed."""
    id: str
    title: str
    summary: str
    link: str
    published: datetime
    source: str
    category: str
    priority: int
    ingested_at: datetime


@router.get("/articles", response_model=List[NewsArticle])
async def get_articles(
    limit: int = Query(default=50, ge=1, le=200),
    category: Optional[str] = Query(default=None)
):
    """Get latest RSS articles."""
    try:
        latest_file = Path("data/rss/latest.json")

        if not latest_file.exists():
            return []

        with open(latest_file, 'r') as f:
            data = json.load(f)

        articles = [NewsArticle(**article) for article in data.get("articles", [])]

        if category:
            articles = [a for a in articles if a.category == category]

        return articles[:limit]

    except Exception as e:
        logger.error("Failed to fetch RSS articles", error=str(e))
        return []


@router.get("/breaking", response_model=List[NewsArticle])
async def get_breaking_news(limit: int = Query(default=10, ge=1, le=50)):
    """Get high-priority breaking news."""
    try:
        latest_file = Path("data/rss/latest.json")

        if not latest_file.exists():
            return []

        with open(latest_file, 'r') as f:
            data = json.load(f)

        articles = [NewsArticle(**article) for article in data.get("articles", [])]
        breaking = [a for a in articles if a.priority >= 8]

        return breaking[:limit]

    except Exception as e:
        logger.error("Failed to fetch breaking news", error=str(e))
        return []


@router.get("/categories")
async def get_categories():
    """Get available news categories."""
    return {
        "categories": [
            {"value": "uk_news", "label": "UK News"},
            {"value": "london_news", "label": "London News"},
            {"value": "breaking", "label": "Breaking News"},
            {"value": "general", "label": "General"}
        ]
    }


@router.get("/stats")
async def get_rss_stats():
    """Get RSS ingestion statistics."""
    try:
        latest_file = Path("data/rss/latest.json")

        if not latest_file.exists():
            return {"total_articles": 0, "last_updated": None}

        with open(latest_file, 'r') as f:
            data = json.load(f)

        return {
            "total_articles": data.get("total_articles", 0),
            "last_updated": data.get("ingested_at"),
            "sources": len(set(a["source"] for a in data.get("articles", [])))
        }

    except Exception as e:
        logger.error("Failed to fetch RSS stats", error=str(e))
        return {"total_articles": 0, "last_updated": None}
