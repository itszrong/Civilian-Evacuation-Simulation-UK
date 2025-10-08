"""
RSS Feed Ingestion Microservice
Asynchronously ingests breaking news from RSS feeds for evacuation planning context
"""

import asyncio
import aiohttp
import feedparser
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional
import structlog
from pydantic import BaseModel, Field
import json
from pathlib import Path
import re

logger = structlog.get_logger(__name__)


class RSSFeedConfig(BaseModel):
    """Configuration for an RSS feed source."""
    name: str
    url: str
    category: str = "general"
    priority: int = Field(default=5, ge=1, le=10)
    enabled: bool = True


class NewsArticle(BaseModel):
    """Structured news article from RSS feed."""
    id: str
    title: str
    summary: str
    link: str
    published: datetime
    source: str
    category: str
    priority: int
    ingested_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    
    # Civil unrest detection fields
    civil_unrest_score: Optional[float] = None
    civil_unrest_indicators: List[str] = Field(default_factory=list)
    requires_simulation: bool = False
    suggested_regions: List[str] = Field(default_factory=list)


class CivilUnrestDetector:
    """Detects civil unrest indicators in news articles."""
    
    def __init__(self):
        # Keywords and phrases that indicate civil unrest or instability
        self.unrest_keywords = {
            'high_risk': [
                'riot', 'riots', 'rioting', 'violent protest', 'violent protests',
                'civil unrest', 'civil disorder', 'mass violence', 'street violence',
                'looting', 'arson', 'vandalism', 'clashes with police',
                'emergency declared', 'state of emergency', 'curfew imposed',
                'martial law', 'national guard deployed', 'troops deployed'
            ],
            'medium_risk': [
                'protest', 'protests', 'demonstration', 'demonstrations',
                'march', 'rally', 'strike', 'blockade', 'occupation',
                'confrontation', 'tensions rising', 'unrest', 'disorder',
                'police presence', 'crowd control', 'public order',
                'disturbance', 'disruption', 'agitation'
            ],
            'low_risk': [
                'gathering', 'assembly', 'meeting', 'vigil',
                'peaceful protest', 'sit-in', 'petition',
                'concerns raised', 'tensions', 'disagreement'
            ]
        }
        
        # London-specific regions and areas
        self.london_regions = [
            'central london', 'city of london', 'westminster', 'camden',
            'islington', 'hackney', 'tower hamlets', 'greenwich', 'lewisham',
            'southwark', 'lambeth', 'wandsworth', 'hammersmith', 'fulham',
            'kensington', 'chelsea', 'brent', 'ealing', 'hounslow',
            'richmond', 'kingston', 'merton', 'sutton', 'croydon',
            'bromley', 'bexley', 'havering', 'barking', 'dagenham',
            'redbridge', 'newham', 'waltham forest', 'haringey', 'enfield',
            'barnet', 'harrow', 'hillingdon'
        ]
    
    def analyze_article(self, article: NewsArticle) -> NewsArticle:
        """Analyze an article for civil unrest indicators."""
        text = f"{article.title} {article.summary}".lower()
        
        # Calculate unrest score
        score = 0.0
        indicators = []
        
        # Check for high-risk keywords
        for keyword in self.unrest_keywords['high_risk']:
            if keyword in text:
                score += 3.0
                indicators.append(f"High-risk: {keyword}")
        
        # Check for medium-risk keywords
        for keyword in self.unrest_keywords['medium_risk']:
            if keyword in text:
                score += 1.5
                indicators.append(f"Medium-risk: {keyword}")
        
        # Check for low-risk keywords
        for keyword in self.unrest_keywords['low_risk']:
            if keyword in text:
                score += 0.5
                indicators.append(f"Low-risk: {keyword}")
        
        # Boost score for London-specific content
        london_mentioned = False
        suggested_regions = []
        
        for region in self.london_regions:
            if region in text:
                london_mentioned = True
                suggested_regions.append(region.title())
                score += 1.0
        
        if 'london' in text and not london_mentioned:
            london_mentioned = True
            suggested_regions.append('Central London')
            score += 1.0
        
        # Normalize score (0-10 scale)
        normalized_score = min(score, 10.0)
        
        # Determine if simulation is required (score >= 4.0 and London-related)
        requires_simulation = normalized_score >= 4.0 and london_mentioned
        
        # Update article with analysis results
        article.civil_unrest_score = normalized_score
        article.civil_unrest_indicators = indicators[:10]  # Limit to top 10
        article.requires_simulation = requires_simulation
        article.suggested_regions = suggested_regions[:5]  # Limit to top 5
        
        return article


class RSSIngestionService:
    """Async RSS feed ingestion service."""

    def __init__(self, storage_path: str = "data/rss"):
        self.storage_path = Path(storage_path)
        self.storage_path.mkdir(parents=True, exist_ok=True)
        self.feeds: List[RSSFeedConfig] = []
        self.articles: List[NewsArticle] = []
        self.unrest_detector = CivilUnrestDetector()
        self._load_feeds()

    def _load_feeds(self):
        """Load RSS feed configurations."""
        self.feeds = [
            RSSFeedConfig(
                name="BBC News - UK",
                url="http://feeds.bbci.co.uk/news/uk/rss.xml",
                category="uk_news",
                priority=9
            ),
            RSSFeedConfig(
                name="Sky News - UK",
                url="https://feeds.skynews.com/feeds/rss/uk.xml",
                category="uk_news",
                priority=8
            ),
            RSSFeedConfig(
                name="The Guardian - UK",
                url="https://www.theguardian.com/uk-news/rss",
                category="uk_news",
                priority=8
            ),
            RSSFeedConfig(
                name="BBC News - London",
                url="http://feeds.bbci.co.uk/news/england/london/rss.xml",
                category="london_news",
                priority=10
            ),
            RSSFeedConfig(
                name="Reuters - Breaking News",
                url="https://www.reuters.com/rssfeed/breakingviews",
                category="breaking",
                priority=9
            ),
            RSSFeedConfig(
                name="AP News - Top Stories",
                url="https://rsshub.app/apnews/topics/apf-topnews",
                category="breaking",
                priority=8
            )
        ]
        logger.info(f"Loaded {len(self.feeds)} RSS feed configurations")

    async def fetch_feed(self, feed: RSSFeedConfig, session: aiohttp.ClientSession) -> List[NewsArticle]:
        """Fetch and parse a single RSS feed."""
        if not feed.enabled:
            return []

        try:
            logger.info(f"Fetching RSS feed: {feed.name}", url=feed.url)

            async with session.get(feed.url, timeout=aiohttp.ClientTimeout(total=30)) as response:
                if response.status != 200:
                    logger.warning(f"Failed to fetch {feed.name}", status=response.status)
                    return []

                content = await response.text()
                parsed = feedparser.parse(content)

                articles = []
                for entry in parsed.entries[:20]:
                    try:
                        published = datetime.now(timezone.utc)
                        if hasattr(entry, 'published_parsed') and entry.published_parsed:
                            published = datetime(*entry.published_parsed[:6], tzinfo=timezone.utc)

                        article = NewsArticle(
                            id=f"{feed.name}_{hash(entry.link)}",
                            title=entry.get('title', 'No title'),
                            summary=entry.get('summary', entry.get('description', '')),
                            link=entry.get('link', ''),
                            published=published,
                            source=feed.name,
                            category=feed.category,
                            priority=feed.priority
                        )
                        
                        # Analyze article for civil unrest indicators
                        article = self.unrest_detector.analyze_article(article)
                        
                        articles.append(article)
                    except Exception as e:
                        logger.error(f"Failed to parse entry from {feed.name}", error=str(e))
                        continue

                logger.info(f"Fetched {len(articles)} articles from {feed.name}")
                return articles

        except asyncio.TimeoutError:
            logger.error(f"Timeout fetching {feed.name}")
            return []
        except Exception as e:
            logger.error(f"Error fetching {feed.name}", error=str(e))
            return []

    async def ingest_all_feeds(self) -> List[NewsArticle]:
        """Ingest all configured RSS feeds concurrently."""
        logger.info("Starting RSS ingestion for all feeds")

        async with aiohttp.ClientSession() as session:
            tasks = [self.fetch_feed(feed, session) for feed in self.feeds if feed.enabled]
            results = await asyncio.gather(*tasks)

            all_articles = []
            for articles in results:
                all_articles.extend(articles)

            all_articles.sort(key=lambda x: x.published, reverse=True)

            self.articles = all_articles
            await self._save_articles()

            logger.info(f"Ingestion complete: {len(all_articles)} total articles")
            return all_articles

    async def _save_articles(self):
        """Save articles to storage."""
        filepath = self.storage_path / f"articles_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}.json"

        data = {
            "ingested_at": datetime.now(timezone.utc).isoformat(),
            "total_articles": len(self.articles),
            "articles": [article.model_dump(mode='json') for article in self.articles]
        }

        with open(filepath, 'w') as f:
            json.dump(data, f, indent=2, default=str)

        latest_filepath = self.storage_path / "latest.json"
        with open(latest_filepath, 'w') as f:
            json.dump(data, f, indent=2, default=str)

        logger.info(f"Saved {len(self.articles)} articles", filepath=str(filepath))

    def get_latest_articles(self, limit: int = 50, category: Optional[str] = None) -> List[NewsArticle]:
        """Get latest articles, optionally filtered by category."""
        articles = self.articles

        if category:
            articles = [a for a in articles if a.category == category]

        return articles[:limit]

    def get_breaking_news(self, limit: int = 10) -> List[NewsArticle]:
        """Get high-priority breaking news."""
        breaking = [a for a in self.articles if a.priority >= 8]
        return breaking[:limit]
    
    def get_civil_unrest_articles(self, min_score: float = 4.0, limit: int = 20) -> List[NewsArticle]:
        """Get articles with civil unrest indicators above threshold."""
        unrest_articles = [
            a for a in self.articles 
            if a.civil_unrest_score is not None and a.civil_unrest_score >= min_score
        ]
        # Sort by unrest score (highest first)
        unrest_articles.sort(key=lambda x: x.civil_unrest_score or 0, reverse=True)
        return unrest_articles[:limit]
    
    def get_simulation_candidates(self, limit: int = 10) -> List[NewsArticle]:
        """Get articles that require simulation."""
        candidates = [a for a in self.articles if a.requires_simulation]
        # Sort by unrest score and recency
        candidates.sort(key=lambda x: (x.civil_unrest_score or 0, x.published), reverse=True)
        return candidates[:limit]


async def continuous_ingestion(service: RSSIngestionService, interval_minutes: int = 15):
    """Continuously ingest RSS feeds at specified interval."""
    logger.info(f"Starting continuous RSS ingestion (interval: {interval_minutes}m)")

    while True:
        try:
            await service.ingest_all_feeds()
            logger.info(f"Waiting {interval_minutes} minutes until next ingestion")
            await asyncio.sleep(interval_minutes * 60)
        except Exception as e:
            logger.error(f"Error in continuous ingestion", error=str(e))
            await asyncio.sleep(60)


async def main():
    """Main entry point for RSS ingestion service."""
    service = RSSIngestionService()

    await service.ingest_all_feeds()

    await continuous_ingestion(service, interval_minutes=15)


if __name__ == "__main__":
    asyncio.run(main())
