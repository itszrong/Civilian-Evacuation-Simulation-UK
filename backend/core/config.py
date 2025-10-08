"""
Configuration management for London Evacuation Planning Tool.
"""

from functools import lru_cache
from typing import List, Optional
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings."""

    # Basic app settings
    DEBUG: bool = Field(default=True, env="DEBUG")
    HOST: str = Field(default="0.0.0.0", env="HOST")
    PORT: int = Field(default=8000, env="PORT")

    # CORS settings
    ALLOWED_ORIGINS: str = Field(
        default="http://localhost:3000,http://127.0.0.1:3000",
        env="ALLOWED_ORIGINS"
    )

    @field_validator('ALLOWED_ORIGINS', mode='before')
    @classmethod
    def parse_allowed_origins(cls, v):
        if isinstance(v, str):
            return v
        if isinstance(v, list):
            return ','.join(v)
        return v

    @property
    def allowed_origins_list(self) -> List[str]:
        """Get ALLOWED_ORIGINS as a list."""
        return [origin.strip() for origin in self.ALLOWED_ORIGINS.split(',')]
    
    # Database settings
    DATABASE_URL: str = Field(
        default="sqlite:///./evacuation_planning.db",
        env="DATABASE_URL"
    )
    
    # Redis settings
    REDIS_URL: str = Field(default="redis://localhost:6379", env="REDIS_URL")
    
    # Storage settings
    S3_BUCKET: Optional[str] = Field(default=None, env="S3_BUCKET")
    S3_ENDPOINT: Optional[str] = Field(default=None, env="S3_ENDPOINT")
    S3_ACCESS_KEY: Optional[str] = Field(default=None, env="S3_ACCESS_KEY")
    S3_SECRET_KEY: Optional[str] = Field(default=None, env="S3_SECRET_KEY")
    LOCAL_STORAGE_PATH: str = Field(default="../local_s3", env="LOCAL_STORAGE_PATH")
    
    # AI/LLM settings
    OPENAI_API_KEY: Optional[str] = Field(default=None, env="OPENAI_API_KEY")
    ANTHROPIC_API_KEY: Optional[str] = Field(default=None, env="ANTHROPIC_API_KEY")
    
    # Data feeds settings
    FETCH_INTERVAL_MINUTES: int = Field(default=30, env="FETCH_INTERVAL_MINUTES")
    SOURCES_CONFIG_PATH: str = Field(
        default="./backend/configs/sources.yml",
        env="SOURCES_CONFIG_PATH"
    )
    
    # Simulation settings
    MAX_SCENARIOS_PER_RUN: int = Field(default=12, env="MAX_SCENARIOS_PER_RUN")
    MAX_COMPUTE_MINUTES: int = Field(default=5, env="MAX_COMPUTE_MINUTES")
    LONDON_GRAPH_CACHE_PATH: str = Field(
        default="./cache/london_graph.pkl",
        env="LONDON_GRAPH_CACHE_PATH"
    )
    
    # RAG settings
    VECTOR_INDEX_PATH: str = Field(
        default="./cache/vector_index",
        env="VECTOR_INDEX_PATH"
    )
    MAX_CITATIONS: int = Field(default=8, env="MAX_CITATIONS")
    FRESHNESS_DAYS_DEFAULT: int = Field(default=7, env="FRESHNESS_DAYS_DEFAULT")
    
    model_config = {
        "env_file": ".env",
        "case_sensitive": True,
        "extra": "ignore"
    }


@lru_cache()
def get_settings() -> Settings:
    """Get cached application settings."""
    return Settings()
