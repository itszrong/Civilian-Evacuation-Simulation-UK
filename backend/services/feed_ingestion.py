"""
Data feed ingestion service for London Evacuation Planning Tool.

This module handles fetching and normalizing data from allow-listed sources
including GOV.UK APIs, TfL feeds, Environment Agency, and verified news sources.
"""

import asyncio
import hashlib
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from urllib.parse import urljoin, urlparse
import xml.etree.ElementTree as ET

import aiohttp
import feedparser
import structlog
import yaml
from pydantic import BaseModel

from core.config import get_settings
from models.schemas import CanonicalDocument, SourceTier, DocumentType, SourcesConfig
from services.storage_service import StorageService

logger = structlog.get_logger(__name__)


class FeedSource(BaseModel):
    """Configuration for a single data source."""
    name: str
    type: str  # "api", "rss"
    base: Optional[str] = None
    url: Optional[str] = None
    description: Optional[str] = None


class FeedTierConfig(BaseModel):
    """Configuration for a source tier."""
    name: str
    freshness_days: int
    sources: List[FeedSource]


class FeedIngestorPolicies(BaseModel):
    """Ingestion policies for respecting source requirements."""
    obey_robots: bool = True
    rate_limit_rpm: int = 30
    user_agent: str = "LondonEvacBot/1.0"
    timeout_seconds: int = 30
    retry_attempts: int = 3
    cache_ttl_hours: int = 1


class FeedIngestorConfig(BaseModel):
    """Complete feed ingestor configuration."""
    tiers: List[FeedTierConfig]
    policies: FeedIngestorPolicies


class FeedIngestorService:
    """Service for ingesting data from allow-listed sources."""

    def __init__(self, storage_service: StorageService):
        self.settings = get_settings()
        self.storage = storage_service
        self.config = self._load_config()
        self.session: Optional[aiohttp.ClientSession] = None
        self._rate_limiter = {}  # Track request times per domain
        
    def _load_config(self) -> FeedIngestorConfig:
        """Load sources configuration from YAML file."""
        try:
            with open(self.settings.SOURCES_CONFIG_PATH, 'r') as f:
                config_data = yaml.safe_load(f)
            
            # Convert to Pydantic model for validation
            return FeedIngestorConfig(**config_data)
        except Exception as e:
            logger.error("Failed to load sources config", error=str(e))
            # Return minimal default config
            return FeedIngestorConfig(
                tiers=[],
                policies=FeedIngestorPolicies()
            )

    async def _get_session(self) -> aiohttp.ClientSession:
        """Get or create aiohttp session with proper headers."""
        if self.session is None or self.session.closed:
            timeout = aiohttp.ClientTimeout(total=self.config.policies.timeout_seconds)
            headers = {
                'User-Agent': self.config.policies.user_agent,
                'Accept': 'application/json, application/xml, text/html, */*',
                'Accept-Encoding': 'gzip, deflate',
            }
            self.session = aiohttp.ClientSession(
                timeout=timeout,
                headers=headers
            )
        return self.session

    async def _check_robots_txt(self, domain: str, path: str) -> bool:
        """Check if robots.txt allows accessing the given path."""
        if not self.config.policies.obey_robots:
            return True
            
        try:
            robots_url = f"https://{domain}/robots.txt"
            session = await self._get_session()
            
            async with session.get(robots_url) as response:
                if response.status == 200:
                    robots_content = await response.text()
                    # Simple robots.txt parsing - in production, use a proper parser
                    if "Disallow: /" in robots_content and self.config.policies.user_agent in robots_content:
                        return False
            return True
        except Exception as e:
            logger.warning("Failed to check robots.txt", domain=domain, error=str(e))
            return True  # Allow by default if can't check

    async def _rate_limit_check(self, domain: str) -> None:
        """Check and enforce rate limiting per domain."""
        now = datetime.utcnow()
        
        if domain not in self._rate_limiter:
            self._rate_limiter[domain] = []
        
        # Clean old requests (older than 1 minute)
        minute_ago = now - timedelta(minutes=1)
        self._rate_limiter[domain] = [
            req_time for req_time in self._rate_limiter[domain]
            if req_time > minute_ago
        ]
        
        # Check if we're over the rate limit
        requests_in_minute = len(self._rate_limiter[domain])
        if requests_in_minute >= self.config.policies.rate_limit_rpm:
            # Calculate sleep time
            oldest_request = min(self._rate_limiter[domain])
            sleep_time = 60 - (now - oldest_request).total_seconds()
            if sleep_time > 0:
                logger.info("Rate limiting", domain=domain, sleep_seconds=sleep_time)
                await asyncio.sleep(sleep_time)
        
        # Record this request
        self._rate_limiter[domain].append(now)

    async def _fetch_rss_feed(self, source: FeedSource, tier: str) -> List[CanonicalDocument]:
        """Fetch and parse RSS feed from a source."""
        if not source.url:
            logger.error("RSS source missing URL", source=source.name)
            return []
        
        parsed_url = urlparse(source.url)
        domain = parsed_url.netloc
        
        # Check robots.txt and rate limiting
        if not await self._check_robots_txt(domain, parsed_url.path):
            logger.warning("Robots.txt disallows access", source=source.name, url=source.url)
            return []
        
        await self._rate_limit_check(domain)
        
        try:
            session = await self._get_session()
            async with session.get(source.url) as response:
                if response.status != 200:
                    logger.error("Failed to fetch RSS feed", 
                               source=source.name, 
                               status=response.status)
                    return []
                
                content = await response.text()
                
            # Parse RSS feed
            feed = feedparser.parse(content)
            documents = []
            fetched_at = datetime.utcnow()
            
            for entry in feed.entries:
                # Extract relevant fields
                title = getattr(entry, 'title', '')
                content_text = self._extract_text_content(entry)
                published_str = getattr(entry, 'published', '')
                link = getattr(entry, 'link', source.url)
                
                # Parse publication date
                try:
                    if published_str:
                        published_at = datetime(*entry.published_parsed[:6])
                    else:
                        published_at = fetched_at
                except (AttributeError, TypeError, ValueError):
                    published_at = fetched_at
                
                # Create document hash
                content_hash = hashlib.sha256(content_text.encode()).hexdigest()
                doc_id = hashlib.sha256(f"{source.name}:{link}".encode()).hexdigest()
                
                # Determine document type based on content
                doc_type = self._classify_document_type(title, content_text, source.name)
                
                # Extract entities (simple keyword extraction)
                entities = self._extract_entities(title + " " + content_text)
                
                document = CanonicalDocument(
                    doc_id=doc_id,
                    url=link,
                    source=source.name,
                    tier=SourceTier(tier),
                    published_at=published_at,
                    fetched_at=fetched_at,
                    title=title,
                    text=content_text,
                    type=doc_type,
                    jurisdiction="UK",  # All sources are UK-focused
                    entities=entities,
                    hash=content_hash
                )
                
                documents.append(document)
                
            logger.info("Successfully fetched RSS feed", 
                       source=source.name, 
                       documents_count=len(documents))
            return documents
            
        except Exception as e:
            logger.error("Failed to fetch RSS feed", 
                        source=source.name, 
                        error=str(e))
            return []

    async def _fetch_api_content(self, source: FeedSource, tier: str) -> List[CanonicalDocument]:
        """Fetch content from API sources."""
        if not source.base:
            logger.error("API source missing base URL", source=source.name)
            return []
        
        # For now, implement basic API fetching
        # In production, this would be customized per API
        parsed_url = urlparse(source.base)
        domain = parsed_url.netloc
        
        await self._rate_limit_check(domain)
        
        try:
            session = await self._get_session()
            
            # Example API endpoints - customize based on actual APIs
            endpoints = [
                "/search?q=emergency",
                "/search?q=evacuation", 
                "/search?q=transport",
            ]
            
            documents = []
            fetched_at = datetime.utcnow()
            
            for endpoint in endpoints:
                url = urljoin(source.base, endpoint)
                
                try:
                    async with session.get(url) as response:
                        if response.status != 200:
                            continue
                            
                        data = await response.json()
                        
                        # Process API response (structure depends on API)
                        api_documents = self._process_api_response(
                            data, source, tier, fetched_at
                        )
                        documents.extend(api_documents)
                        
                except Exception as e:
                    logger.warning("Failed to fetch from API endpoint", 
                                 source=source.name, 
                                 endpoint=endpoint, 
                                 error=str(e))
                    continue
            
            logger.info("Successfully fetched API content", 
                       source=source.name, 
                       documents_count=len(documents))
            return documents
            
        except Exception as e:
            logger.error("Failed to fetch API content", 
                        source=source.name, 
                        error=str(e))
            return []

    def _extract_text_content(self, entry) -> str:
        """Extract text content from RSS entry."""
        content_fields = ['summary', 'description', 'content']
        content_parts = []
        
        for field in content_fields:
            if hasattr(entry, field):
                value = getattr(entry, field)
                if isinstance(value, list):
                    # Handle multiple content blocks
                    for item in value:
                        if isinstance(item, dict) and 'value' in item:
                            content_parts.append(item['value'])
                        else:
                            content_parts.append(str(item))
                else:
                    content_parts.append(str(value))
        
        # Join and clean up HTML tags (basic cleaning)
        content = " ".join(content_parts)
        # Remove HTML tags (basic regex - use proper HTML parser in production)
        import re
        content = re.sub(r'<[^>]+>', '', content)
        content = re.sub(r'\s+', ' ', content).strip()
        
        return content

    def _classify_document_type(self, title: str, content: str, source: str) -> DocumentType:
        """Classify document type based on content and source."""
        text = (title + " " + content).lower()
        
        # Classification keywords
        alert_keywords = ['alert', 'warning', 'urgent', 'emergency', 'incident', 'closure']
        policy_keywords = ['policy', 'guidance', 'framework', 'strategy', 'plan']
        
        if any(keyword in text for keyword in alert_keywords):
            return DocumentType.ALERT
        elif any(keyword in text for keyword in policy_keywords):
            return DocumentType.POLICY
        else:
            return DocumentType.NEWS

    def _extract_entities(self, text: str) -> List[str]:
        """Extract location and infrastructure entities from text."""
        # Simple keyword-based entity extraction
        # In production, use proper NER models
        entities = []
        
        # London locations and infrastructure
        london_entities = [
            'Thames', 'Westminster', 'London Bridge', 'Tower Bridge',
            'Lambeth', 'Southwark', 'Camden', 'Islington', 'Hackney',
            'Greenwich', 'Lewisham', 'Wembley', 'Heathrow', 'Gatwick',
            'St Thomas Hospital', 'Kings College Hospital', 'London Eye',
            'Big Ben', 'Parliament', 'Buckingham Palace', 'Tate Britain'
        ]
        
        text_lower = text.lower()
        for entity in london_entities:
            if entity.lower() in text_lower:
                entities.append(entity)
        
        return list(set(entities))  # Remove duplicates

    def _process_api_response(self, data: Any, source: FeedSource, tier: str, 
                            fetched_at: datetime) -> List[CanonicalDocument]:
        """Process API response into canonical documents."""
        documents = []
        
        # This is a placeholder implementation
        # Each API would need custom processing logic
        
        if isinstance(data, dict) and 'results' in data:
            for item in data.get('results', []):
                if isinstance(item, dict):
                    title = item.get('title', '')
                    content = item.get('content', item.get('description', ''))
                    url = item.get('url', source.base)
                    
                    if title and content:
                        doc_id = hashlib.sha256(f"{source.name}:{url}".encode()).hexdigest()
                        content_hash = hashlib.sha256(content.encode()).hexdigest()
                        
                        document = CanonicalDocument(
                            doc_id=doc_id,
                            url=url,
                            source=source.name,
                            tier=SourceTier(tier),
                            published_at=fetched_at,
                            fetched_at=fetched_at,
                            title=title,
                            text=content,
                            type=self._classify_document_type(title, content, source.name),
                            jurisdiction="UK",
                            entities=self._extract_entities(title + " " + content),
                            hash=content_hash
                        )
                        documents.append(document)
        
        return documents

    async def fetch_all_sources(self) -> Dict[str, Any]:
        """Fetch from all configured sources and return summary."""
        logger.info("Starting feed ingestion for all sources")
        
        total_fetched = 0
        total_updated = 0
        total_errors = 0
        tier_results = {}
        
        for tier_config in self.config.tiers:
            tier_name = tier_config.name
            tier_results[tier_name] = {
                'sources': [],
                'total_documents': 0,
                'errors': 0
            }
            
            for source in tier_config.sources:
                logger.info("Fetching from source", 
                           source=source.name, 
                           type=source.type, 
                           tier=tier_name)
                
                try:
                    if source.type == 'rss':
                        documents = await self._fetch_rss_feed(source, tier_name)
                    elif source.type == 'api':
                        documents = await self._fetch_api_content(source, tier_name)
                    else:
                        logger.warning("Unknown source type", 
                                     source=source.name, 
                                     type=source.type)
                        continue
                    
                    # Store documents
                    stored_count = 0
                    for doc in documents:
                        try:
                            await self.storage.store_document(doc, tier_name)
                            stored_count += 1
                        except Exception as e:
                            logger.error("Failed to store document", 
                                       doc_id=doc.doc_id, 
                                       error=str(e))
                    
                    tier_results[tier_name]['sources'].append({
                        'name': source.name,
                        'type': source.type,
                        'documents_fetched': len(documents),
                        'documents_stored': stored_count,
                        'status': 'success'
                    })
                    
                    tier_results[tier_name]['total_documents'] += stored_count
                    total_fetched += len(documents)
                    total_updated += stored_count
                    
                except Exception as e:
                    logger.error("Source fetch failed", 
                               source=source.name, 
                               error=str(e))
                    
                    tier_results[tier_name]['sources'].append({
                        'name': source.name,
                        'type': source.type,
                        'documents_fetched': 0,
                        'documents_stored': 0,
                        'status': 'error',
                        'error': str(e)
                    })
                    
                    tier_results[tier_name]['errors'] += 1
                    total_errors += 1
        
        # Close session
        if self.session:
            await self.session.close()
            self.session = None
        
        result = {
            'fetched': total_fetched,
            'updated': total_updated,
            'errors': total_errors,
            'timestamp': datetime.utcnow().isoformat(),
            'tiers': tier_results
        }
        
        logger.info("Feed ingestion completed", 
                   fetched=total_fetched, 
                   updated=total_updated, 
                   errors=total_errors)
        
        return result

    async def get_ingestion_status(self) -> Dict[str, Any]:
        """Get status of all configured sources."""
        status = {
            'timestamp': datetime.utcnow().isoformat(),
            'feeds': {},
            'total_documents': 0,
            'last_global_refresh': None
        }
        
        for tier_config in self.config.tiers:
            tier_name = tier_config.name
            tier_status = {
                'sources': []
            }
            
            for source in tier_config.sources:
                # Get source status from storage
                source_status = await self.storage.get_source_status(source.name)
                
                tier_status['sources'].append({
                    'name': source.name,
                    'last_updated': source_status.get('last_updated'),
                    'last_error': source_status.get('last_error'),
                    'documents_count': source_status.get('documents_count', 0),
                    'status': source_status.get('status', 'configured')
                })
                
                status['total_documents'] += source_status.get('documents_count', 0)
            
            status['feeds'][tier_name] = tier_status
        
        # Get last global refresh time
        status['last_global_refresh'] = await self.storage.get_last_refresh_time()
        
        return status
