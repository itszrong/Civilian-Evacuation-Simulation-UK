"""
Pytest configuration and shared fixtures for the backend test suite.
"""

import asyncio
import os
import tempfile
import shutil
from pathlib import Path
from typing import Dict, Any, Generator, AsyncGenerator
from unittest.mock import Mock, AsyncMock, patch

import pytest
import pandas as pd
from fastapi.testclient import TestClient
from httpx import AsyncClient

from core.config import Settings, get_settings
from main import create_application
from models.schemas import (
    UserIntent, ScenarioConstraints, UserPreferences, 
    SourceTier, TaskStatus, AgentType
)


@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def test_settings() -> Settings:
    """Create test settings with safe defaults."""
    return Settings(
        DEBUG=True,
        HOST="127.0.0.1",
        PORT=8001,
        DATABASE_URL="sqlite:///:memory:",
        REDIS_URL="redis://localhost:6379/1",
        LOCAL_STORAGE_PATH="./test_storage",
        OPENAI_API_KEY="test-key",
        ANTHROPIC_API_KEY="test-key",
        SOURCES_CONFIG_PATH="./tests/fixtures/test_sources.yml",
        VECTOR_INDEX_PATH="./test_cache/vector_index",
        LONDON_GRAPH_CACHE_PATH="./test_cache/london_graph.pkl",
        ALLOWED_ORIGINS="http://localhost:3000"
    )


@pytest.fixture
def temp_storage_dir() -> Generator[str, None, None]:
    """Create a temporary directory for test storage."""
    temp_dir = tempfile.mkdtemp()
    yield temp_dir
    shutil.rmtree(temp_dir, ignore_errors=True)


@pytest.fixture
def mock_settings(test_settings: Settings):
    """Mock the get_settings function to return test settings."""
    with patch('core.config.get_settings', return_value=test_settings):
        yield test_settings


@pytest.fixture
def app(mock_settings):
    """Create FastAPI test application."""
    return create_application()


@pytest.fixture
def client(app) -> TestClient:
    """Create test client for FastAPI app."""
    return TestClient(app)


@pytest.fixture
async def async_client(app) -> AsyncGenerator[AsyncClient, None]:
    """Create async test client for FastAPI app."""
    async with AsyncClient(app=app, base_url="http://test") as ac:
        yield ac


@pytest.fixture
def sample_user_intent() -> UserIntent:
    """Create a sample user intent for testing."""
    return UserIntent(
        objective="Test evacuation scenario for central London",
        city="london",
        constraints=ScenarioConstraints(
            max_scenarios=5,
            compute_budget_minutes=2,
            must_protect_pois=["Westminster", "London Bridge"]
        ),
        hypotheses=["Transport hubs will be congested", "Emergency services need priority routes"],
        preferences=UserPreferences(
            fairness_weight=0.3,
            clearance_weight=0.5,
            robustness_weight=0.2
        ),
        freshness_days=7,
        tiers=[SourceTier.GOV_PRIMARY]
    )


@pytest.fixture
def sample_timeseries_data() -> pd.DataFrame:
    """Create sample timeseries data for testing."""
    return pd.DataFrame({
        'run_id': ['test_run'] * 20,
        't': list(range(0, 1200, 60)),  # 20 minutes in 60-second intervals
        'k': ['clearance_pct'] * 10 + ['queue_len'] * 10,
        'scope': ['city'] * 10 + ['edge:123'] * 10,
        'v': [i * 5 for i in range(10)] + [10 - i for i in range(10)]
    })


@pytest.fixture
def sample_events_data() -> pd.DataFrame:
    """Create sample events data for testing."""
    return pd.DataFrame({
        'run_id': ['test_run'] * 5,
        't': [0, 120, 300, 600, 900],
        'type': ['start', 'capacity_warning', 'emergency', 'capacity_warning', 'end'],
        'id': ['sim_start', 'warn_1', 'fire_alarm', 'warn_2', 'sim_end'],
        'attrs': ['{}', '{"location": "station_a"}', '{"severity": "high"}', '{"location": "station_b"}', '{}']
    })


@pytest.fixture
def mock_openai_client():
    """Mock OpenAI client for testing."""
    mock_client = Mock()
    mock_response = Mock()
    mock_response.choices = [Mock()]
    mock_response.choices[0].message.content = "Test AI response"
    mock_client.chat.completions.create.return_value = mock_response
    return mock_client


@pytest.fixture
def mock_anthropic_client():
    """Mock Anthropic client for testing."""
    mock_client = Mock()
    mock_response = Mock()
    mock_response.content = [Mock()]
    mock_response.content[0].text = "Test Claude response"
    mock_client.messages.create.return_value = mock_response
    return mock_client


@pytest.fixture
def sample_scenario_config() -> Dict[str, Any]:
    """Create a sample scenario configuration."""
    return {
        "id": "test_scenario_001",
        "city": "london",
        "seed": 42,
        "closures": [
            {
                "type": "polygon_cordon",
                "area": "Westminster",
                "start_minute": 0,
                "end_minute": 60
            }
        ],
        "capacity_changes": [
            {
                "edge_selector": "tube_lines",
                "multiplier": 0.5
            }
        ],
        "protected_corridors": [
            {
                "name": "Emergency Route 1",
                "rule": "emergency_services",
                "multiplier": 1.5
            }
        ],
        "staged_egress": [
            {
                "area": "City of London",
                "start_minute": 10,
                "release_rate": "gradual"
            }
        ],
        "notes": "Test scenario for unit testing"
    }


@pytest.fixture
def sample_simulation_metrics() -> Dict[str, float]:
    """Create sample simulation metrics."""
    return {
        "clearance_time": 1800.0,  # 30 minutes
        "max_queue": 150.0,
        "fairness_index": 0.85,
        "robustness": 0.75
    }


@pytest.fixture
def mock_redis():
    """Mock Redis client for testing."""
    mock_redis = Mock()
    mock_redis.get.return_value = None
    mock_redis.set.return_value = True
    mock_redis.delete.return_value = True
    mock_redis.exists.return_value = False
    return mock_redis


@pytest.fixture
def mock_storage_service():
    """Mock storage service for testing."""
    mock_service = Mock()
    mock_service.store_file = AsyncMock(return_value="test_file_id")
    mock_service.retrieve_file = AsyncMock(return_value=b"test file content")
    mock_service.delete_file = AsyncMock(return_value=True)
    mock_service.list_files = AsyncMock(return_value=["file1.json", "file2.csv"])
    return mock_service


@pytest.fixture
def sample_sources_config() -> str:
    """Create a sample sources configuration YAML."""
    return """
tiers:
  - name: gov_primary
    freshness_days: 7
    sources:
      - name: gov_uk
        type: api
        base: https://www.gov.uk
        url: /api/content
      - name: london_gov
        type: rss
        url: https://www.london.gov.uk/rss

  - name: news_verified
    freshness_days: 3
    sources:
      - name: bbc_news
        type: rss
        url: https://feeds.bbci.co.uk/news/rss.xml
      - name: guardian
        type: rss
        url: https://www.theguardian.com/uk/rss

policies:
  max_docs_per_source: 100
  min_confidence_score: 0.7
  deduplication_threshold: 0.9
"""


@pytest.fixture
def create_test_sources_config(temp_storage_dir, sample_sources_config):
    """Create a test sources configuration file."""
    config_path = Path(temp_storage_dir) / "test_sources.yml"
    config_path.write_text(sample_sources_config)
    return str(config_path)


# Async fixtures for testing async functions
@pytest.fixture
async def mock_async_openai():
    """Mock async OpenAI client."""
    mock_client = AsyncMock()
    mock_response = Mock()
    mock_response.choices = [Mock()]
    mock_response.choices[0].message.content = "Async test AI response"
    mock_client.chat.completions.create.return_value = mock_response
    return mock_client


@pytest.fixture
async def mock_async_anthropic():
    """Mock async Anthropic client."""
    mock_client = AsyncMock()
    mock_response = Mock()
    mock_response.content = [Mock()]
    mock_response.content[0].text = "Async test Claude response"
    mock_client.messages.create.return_value = mock_response
    return mock_client


# Test data creation helpers
def create_test_parquet_files(storage_dir: str, run_id: str, 
                             timeseries_data: pd.DataFrame, 
                             events_data: pd.DataFrame):
    """Helper to create test parquet files."""
    storage_path = Path(storage_dir)
    storage_path.mkdir(exist_ok=True)
    
    timeseries_path = storage_path / f"timeseries_{run_id}.parquet"
    events_path = storage_path / f"events_{run_id}.parquet"
    
    timeseries_data.to_parquet(timeseries_path)
    events_data.to_parquet(events_path)
    
    return str(timeseries_path), str(events_path)


# Pytest markers for different test categories
pytest_plugins = []

# Custom markers
def pytest_configure(config):
    """Configure custom pytest markers."""
    config.addinivalue_line("markers", "unit: mark test as a unit test")
    config.addinivalue_line("markers", "integration: mark test as an integration test")
    config.addinivalue_line("markers", "api: mark test as an API test")
    config.addinivalue_line("markers", "slow: mark test as slow running")
    config.addinivalue_line("markers", "requires_ai: mark test as requiring AI services")
    config.addinivalue_line("markers", "requires_redis: mark test as requiring Redis")
