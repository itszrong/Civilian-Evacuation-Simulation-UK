"""
Civil Unrest Detection API
Integrates RSS feed analysis with simulation queue
"""

from fastapi import APIRouter, HTTPException
from typing import List, Dict, Any, Optional
from pydantic import BaseModel
import json
from pathlib import Path
import sys
import os

# Add services to path
sys.path.append(os.path.join(os.path.dirname(__file__), '../../services'))

from api.simulation_queue import queue_service, SimulationRequest

router = APIRouter(prefix="/api/civil-unrest", tags=["civil-unrest"])


class UnrestArticle(BaseModel):
    """Article with civil unrest analysis."""
    id: str
    title: str
    summary: str
    link: str
    published: str
    source: str
    civil_unrest_score: float
    civil_unrest_indicators: List[str]
    requires_simulation: bool
    suggested_regions: List[str]


class UnrestAnalysis(BaseModel):
    """Analysis results for civil unrest detection."""
    total_articles: int
    unrest_articles: int
    simulation_candidates: int
    highest_score: float
    articles: List[UnrestArticle]


def load_rss_articles() -> List[Dict[str, Any]]:
    """Load latest RSS articles from the ingestion service."""
    rss_data_path = Path("services/external/rss_ingestion/data/rss/latest.json")
    
    if not rss_data_path.exists():
        return []
    
    try:
        with open(rss_data_path, 'r') as f:
            data = json.load(f)
            return data.get('articles', [])
    except Exception:
        return []


@router.get("/analysis", response_model=UnrestAnalysis)
async def get_unrest_analysis(min_score: float = 1.0, limit: int = 50):
    """Get civil unrest analysis from RSS feeds."""
    articles = load_rss_articles()
    
    # Filter articles with unrest scores
    unrest_articles = [
        article for article in articles
        if article.get('civil_unrest_score', 0) >= min_score
    ]
    
    # Sort by unrest score
    unrest_articles.sort(key=lambda x: x.get('civil_unrest_score', 0), reverse=True)
    
    # Convert to response format
    response_articles = []
    for article in unrest_articles[:limit]:
        response_articles.append(UnrestArticle(
            id=article['id'],
            title=article['title'],
            summary=article['summary'],
            link=article['link'],
            published=article['published'],
            source=article['source'],
            civil_unrest_score=article.get('civil_unrest_score', 0),
            civil_unrest_indicators=article.get('civil_unrest_indicators', []),
            requires_simulation=article.get('requires_simulation', False),
            suggested_regions=article.get('suggested_regions', [])
        ))
    
    simulation_candidates = len([a for a in unrest_articles if a.get('requires_simulation', False)])
    highest_score = max([a.get('civil_unrest_score', 0) for a in unrest_articles], default=0)
    
    return UnrestAnalysis(
        total_articles=len(articles),
        unrest_articles=len(unrest_articles),
        simulation_candidates=simulation_candidates,
        highest_score=highest_score,
        articles=response_articles
    )


@router.get("/candidates", response_model=List[UnrestArticle])
async def get_simulation_candidates():
    """Get articles that require simulation."""
    articles = load_rss_articles()
    
    candidates = [
        article for article in articles
        if article.get('requires_simulation', False)
    ]
    
    # Sort by unrest score and recency
    candidates.sort(key=lambda x: (x.get('civil_unrest_score', 0), x.get('published', '')), reverse=True)
    
    response_articles = []
    for article in candidates:
        response_articles.append(UnrestArticle(
            id=article['id'],
            title=article['title'],
            summary=article['summary'],
            link=article['link'],
            published=article['published'],
            source=article['source'],
            civil_unrest_score=article.get('civil_unrest_score', 0),
            civil_unrest_indicators=article.get('civil_unrest_indicators', []),
            requires_simulation=article.get('requires_simulation', False),
            suggested_regions=article.get('suggested_regions', [])
        ))
    
    return response_articles


@router.post("/queue-simulation/{article_id}")
async def queue_simulation_for_article(article_id: str):
    """Queue a simulation based on an article."""
    articles = load_rss_articles()
    
    # Find the article
    article = None
    for a in articles:
        if a['id'] == article_id:
            article = a
            break
    
    if not article:
        raise HTTPException(status_code=404, detail="Article not found")
    
    if not article.get('requires_simulation', False):
        raise HTTPException(status_code=400, detail="Article does not require simulation")
    
    # Create simulation request
    simulation_request = SimulationRequest(
        article_id=article['id'],
        article_title=article['title'],
        article_summary=article['summary'],
        civil_unrest_score=article.get('civil_unrest_score', 0),
        suggested_regions=article.get('suggested_regions', [])
    )
    
    # Add to queue
    queued_request = queue_service.add_request(simulation_request)
    
    return {
        "message": "Simulation queued successfully",
        "request_id": queued_request.id,
        "status": queued_request.status
    }


@router.post("/auto-queue")
async def auto_queue_simulations(min_score: float = 6.0):
    """Automatically queue simulations for high-risk articles."""
    articles = load_rss_articles()
    
    # Find high-risk articles that require simulation
    candidates = [
        article for article in articles
        if (article.get('requires_simulation', False) and 
            article.get('civil_unrest_score', 0) >= min_score)
    ]
    
    queued_count = 0
    queued_requests = []
    
    for article in candidates:
        simulation_request = SimulationRequest(
            article_id=article['id'],
            article_title=article['title'],
            article_summary=article['summary'],
            civil_unrest_score=article.get('civil_unrest_score', 0),
            suggested_regions=article.get('suggested_regions', [])
        )
        
        # Check if already queued
        existing = queue_service.find_similar_request(simulation_request)
        if not existing:
            queued_request = queue_service.add_request(simulation_request)
            queued_requests.append(queued_request)
            queued_count += 1
    
    return {
        "message": f"Queued {queued_count} simulations",
        "queued_requests": [{"id": req.id, "title": req.article_title} for req in queued_requests],
        "total_candidates": len(candidates)
    }


@router.get("/stats")
async def get_unrest_stats():
    """Get civil unrest detection statistics."""
    articles = load_rss_articles()
    
    if not articles:
        return {
            "total_articles": 0,
            "articles_with_scores": 0,
            "simulation_candidates": 0,
            "average_score": 0,
            "highest_score": 0,
            "score_distribution": {}
        }
    
    articles_with_scores = [a for a in articles if a.get('civil_unrest_score') is not None]
    simulation_candidates = [a for a in articles if a.get('requires_simulation', False)]
    
    scores = [a.get('civil_unrest_score', 0) for a in articles_with_scores]
    average_score = sum(scores) / len(scores) if scores else 0
    highest_score = max(scores) if scores else 0
    
    # Score distribution
    score_distribution = {
        "0-2": len([s for s in scores if 0 <= s < 2]),
        "2-4": len([s for s in scores if 2 <= s < 4]),
        "4-6": len([s for s in scores if 4 <= s < 6]),
        "6-8": len([s for s in scores if 6 <= s < 8]),
        "8-10": len([s for s in scores if 8 <= s <= 10])
    }
    
    return {
        "total_articles": len(articles),
        "articles_with_scores": len(articles_with_scores),
        "simulation_candidates": len(simulation_candidates),
        "average_score": round(average_score, 2),
        "highest_score": round(highest_score, 2),
        "score_distribution": score_distribution
    }
