"""
Search API endpoints for RAG system in London Evacuation Planning Tool.
"""

from typing import List

from fastapi import APIRouter, Query, HTTPException
import structlog

from models.schemas import SearchRequest, SearchResponse, SearchResult, SourceTier
from services.storage_service import StorageService

logger = structlog.get_logger(__name__)
router = APIRouter()

# Initialize storage service
storage_service = StorageService()


@router.get("/search", response_model=SearchResponse)
async def search_documents(
    q: str = Query(..., description="Search query"),
    k: int = Query(default=8, ge=1, le=20, description="Number of results to return"),
    tiers: List[SourceTier] = Query(default=[SourceTier.GOV_PRIMARY], description="Source tiers to search"),
    max_age_days: int = Query(default=7, ge=1, le=30, description="Maximum age of documents in days")
) -> SearchResponse:
    """
    Search documents using vector similarity search.
    
    This endpoint provides the RAG search functionality with:
    - Vector similarity search over ingested documents
    - Filtering by source tier and document age
    - Recency and authority weighting
    
    Args:
        q: Search query string
        k: Number of results to return (1-20)
        tiers: List of source tiers to search in
        max_age_days: Maximum age of documents to consider (1-30 days)
    
    Returns:
        SearchResponse with ranked results including titles, URLs, sources, and scores
    """
    logger.info(
        "Document search requested",
        query=q,
        k=k,
        tiers=[tier.value for tier in tiers],
        max_age_days=max_age_days
    )
    
    try:
        # For now, use simple text search from storage service
        # TODO: Replace with proper vector search implementation
        
        results = []
        
        # Search each tier
        for tier in tiers:
            tier_results = await storage_service.search_documents(
                query=q,
                tier=tier.value,
                max_age_days=max_age_days,
                limit=k
            )
            
            # Convert to SearchResult objects
            for result in tier_results:
                search_result = SearchResult(
                    doc_id=result['doc_id'],
                    title=result['title'],
                    url=result['url'],
                    source=result['source'],
                    published_at=result['published_at'],
                    score=result['score']
                )
                results.append(search_result)
        
        # Sort by score (descending) and limit to k results
        results.sort(key=lambda x: x.score, reverse=True)
        results = results[:k]
        
        return SearchResponse(
            results=results,
            total_count=len(results),
            query=q
        )
        
    except Exception as e:
        logger.error("Search failed", error=str(e), query=q)
        raise HTTPException(
            status_code=500,
            detail=f"Search operation failed: {str(e)}"
        )


@router.post("/search", response_model=SearchResponse)
async def search_documents_post(request: SearchRequest) -> SearchResponse:
    """
    Search documents using POST request body.
    
    Alternative endpoint that accepts search parameters in request body
    for more complex search configurations.
    """
    return await search_documents(
        q=request.query,
        k=request.k,
        tiers=request.tiers,
        max_age_days=request.max_age_days
    )
