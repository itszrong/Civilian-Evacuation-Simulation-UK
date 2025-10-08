"""
Tests for core.config module.
"""

import os
import pytest
from unittest.mock import patch, mock_open
from pydantic import ValidationError

from core.config import Settings, get_settings


class TestSettings:
    """Test the Settings class."""
    
    def test_default_settings(self):
        """Test default settings values."""
        settings = Settings()
        
        assert settings.DEBUG is True
        assert settings.HOST == "0.0.0.0"
        assert settings.PORT == 8000
        assert settings.DATABASE_URL == "sqlite:///./evacuation_planning.db"
        assert settings.REDIS_URL == "redis://localhost:6379"
        assert settings.LOCAL_STORAGE_PATH == "./local_s3"
        assert settings.MAX_SCENARIOS_PER_RUN == 12
        assert settings.MAX_COMPUTE_MINUTES == 5
        assert settings.MAX_CITATIONS == 8
        assert settings.FRESHNESS_DAYS_DEFAULT == 7
    
    def test_environment_variable_override(self):
        """Test that environment variables override defaults."""
        with patch.dict(os.environ, {
            'DEBUG': 'false',
            'HOST': '127.0.0.1',
            'PORT': '9000',
            'DATABASE_URL': 'postgresql://test:test@localhost/testdb',
            'REDIS_URL': 'redis://localhost:6380/1',
            'OPENAI_API_KEY': 'test-openai-key',
            'ANTHROPIC_API_KEY': 'test-anthropic-key',
            'MAX_SCENARIOS_PER_RUN': '20',
            'MAX_COMPUTE_MINUTES': '10'
        }):
            settings = Settings()
            
            assert settings.DEBUG is False
            assert settings.HOST == "127.0.0.1"
            assert settings.PORT == 9000
            assert settings.DATABASE_URL == "postgresql://test:test@localhost/testdb"
            assert settings.REDIS_URL == "redis://localhost:6380/1"
            assert settings.OPENAI_API_KEY == "test-openai-key"
            assert settings.ANTHROPIC_API_KEY == "test-anthropic-key"
            assert settings.MAX_SCENARIOS_PER_RUN == 20
            assert settings.MAX_COMPUTE_MINUTES == 10
    
    def test_allowed_origins_parsing_string(self):
        """Test parsing ALLOWED_ORIGINS from string."""
        settings = Settings(ALLOWED_ORIGINS="http://localhost:3000,https://app.example.com")
        
        expected = ["http://localhost:3000", "https://app.example.com"]
        assert settings.allowed_origins_list == expected
    
    def test_allowed_origins_parsing_list(self):
        """Test parsing ALLOWED_ORIGINS from list."""
        origins = ["http://localhost:3000", "https://app.example.com"]
        settings = Settings(ALLOWED_ORIGINS=origins)
        
        assert settings.allowed_origins_list == origins
    
    def test_allowed_origins_with_spaces(self):
        """Test parsing ALLOWED_ORIGINS with spaces."""
        settings = Settings(ALLOWED_ORIGINS="http://localhost:3000, https://app.example.com , http://test.com")
        
        expected = ["http://localhost:3000", "https://app.example.com", "http://test.com"]
        assert settings.allowed_origins_list == expected
    
    def test_optional_fields_none(self):
        """Test that optional fields can be None."""
        settings = Settings()
        
        assert settings.S3_BUCKET is None
        assert settings.S3_ENDPOINT is None
        assert settings.S3_ACCESS_KEY is None
        assert settings.S3_SECRET_KEY is None
        assert settings.OPENAI_API_KEY is None
        assert settings.ANTHROPIC_API_KEY is None
    
    def test_optional_fields_set(self):
        """Test that optional fields can be set."""
        settings = Settings(
            S3_BUCKET="test-bucket",
            S3_ENDPOINT="https://s3.example.com",
            S3_ACCESS_KEY="test-access-key",
            S3_SECRET_KEY="test-secret-key",
            OPENAI_API_KEY="test-openai-key",
            ANTHROPIC_API_KEY="test-anthropic-key"
        )
        
        assert settings.S3_BUCKET == "test-bucket"
        assert settings.S3_ENDPOINT == "https://s3.example.com"
        assert settings.S3_ACCESS_KEY == "test-access-key"
        assert settings.S3_SECRET_KEY == "test-secret-key"
        assert settings.OPENAI_API_KEY == "test-openai-key"
        assert settings.ANTHROPIC_API_KEY == "test-anthropic-key"
    
    def test_invalid_port(self):
        """Test validation of invalid port numbers."""
        with pytest.raises(ValidationError):
            Settings(PORT=-1)
        
        with pytest.raises(ValidationError):
            Settings(PORT=70000)
    
    def test_invalid_max_scenarios(self):
        """Test validation of max scenarios."""
        with pytest.raises(ValidationError):
            Settings(MAX_SCENARIOS_PER_RUN=0)
        
        with pytest.raises(ValidationError):
            Settings(MAX_SCENARIOS_PER_RUN=-5)
    
    def test_invalid_max_compute_minutes(self):
        """Test validation of max compute minutes."""
        with pytest.raises(ValidationError):
            Settings(MAX_COMPUTE_MINUTES=0)
        
        with pytest.raises(ValidationError):
            Settings(MAX_COMPUTE_MINUTES=-1)
    
    def test_invalid_freshness_days(self):
        """Test validation of freshness days."""
        with pytest.raises(ValidationError):
            Settings(FRESHNESS_DAYS_DEFAULT=0)
        
        with pytest.raises(ValidationError):
            Settings(FRESHNESS_DAYS_DEFAULT=50)  # Assuming max is 30
    
    def test_case_sensitive_env_vars(self):
        """Test that environment variables are case sensitive."""
        with patch.dict(os.environ, {
            'debug': 'false',  # lowercase should not work
            'DEBUG': 'false'   # uppercase should work
        }):
            settings = Settings()
            assert settings.DEBUG is False
    
    def test_extra_fields_ignored(self):
        """Test that extra fields are ignored."""
        # This should not raise an error due to extra="ignore"
        settings = Settings(UNKNOWN_FIELD="test")
        assert not hasattr(settings, 'UNKNOWN_FIELD')
    
    def test_model_config(self):
        """Test model configuration."""
        settings = Settings()
        
        # Check that the model config is properly set
        assert settings.model_config["env_file"] == ".env"
        assert settings.model_config["case_sensitive"] is True
        assert settings.model_config["extra"] == "ignore"


class TestGetSettings:
    """Test the get_settings function."""
    
    def test_get_settings_returns_settings_instance(self):
        """Test that get_settings returns a Settings instance."""
        settings = get_settings()
        assert isinstance(settings, Settings)
    
    def test_get_settings_caching(self):
        """Test that get_settings caches the result."""
        settings1 = get_settings()
        settings2 = get_settings()
        
        # Should return the same instance due to lru_cache
        assert settings1 is settings2
    
    @patch('core.config.Settings')
    def test_get_settings_calls_settings_constructor(self, mock_settings):
        """Test that get_settings calls Settings constructor."""
        mock_instance = mock_settings.return_value
        
        # Clear the cache first
        get_settings.cache_clear()
        
        result = get_settings()
        
        mock_settings.assert_called_once()
        assert result is mock_instance
    
    def test_get_settings_with_env_file(self):
        """Test get_settings with environment file."""
        # Create a mock .env file content
        env_content = """
DEBUG=false
HOST=test.example.com
PORT=9999
OPENAI_API_KEY=test-key-from-file
"""
        
        with patch("builtins.open", mock_open(read_data=env_content)):
            with patch.dict(os.environ, {}, clear=True):
                # Clear cache to ensure fresh load
                get_settings.cache_clear()
                
                settings = get_settings()
                
                # Note: The actual .env file loading is handled by pydantic-settings
                # This test mainly ensures the function works without errors
                assert isinstance(settings, Settings)


@pytest.mark.unit
class TestSettingsIntegration:
    """Integration tests for Settings with various configurations."""
    
    def test_production_like_settings(self):
        """Test production-like settings configuration."""
        production_env = {
            'DEBUG': 'false',
            'HOST': '0.0.0.0',
            'PORT': '8000',
            'DATABASE_URL': 'postgresql://user:pass@db:5432/evacuation',
            'REDIS_URL': 'redis://redis:6379/0',
            'S3_BUCKET': 'evacuation-storage',
            'S3_ENDPOINT': 'https://s3.amazonaws.com',
            'S3_ACCESS_KEY': 'AKIAIOSFODNN7EXAMPLE',
            'S3_SECRET_KEY': 'wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY',
            'OPENAI_API_KEY': 'sk-test-key',
            'ANTHROPIC_API_KEY': 'claude-test-key',
            'LOCAL_STORAGE_PATH': '/app/storage',
            'MAX_SCENARIOS_PER_RUN': '15',
            'MAX_COMPUTE_MINUTES': '8',
            'ALLOWED_ORIGINS': 'https://evacuation.gov.uk,https://admin.evacuation.gov.uk'
        }
        
        with patch.dict(os.environ, production_env):
            settings = Settings()
            
            assert settings.DEBUG is False
            assert settings.HOST == "0.0.0.0"
            assert settings.PORT == 8000
            assert settings.DATABASE_URL == "postgresql://user:pass@db:5432/evacuation"
            assert settings.REDIS_URL == "redis://redis:6379/0"
            assert settings.S3_BUCKET == "evacuation-storage"
            assert settings.OPENAI_API_KEY == "sk-test-key"
            assert settings.ANTHROPIC_API_KEY == "claude-test-key"
            assert settings.MAX_SCENARIOS_PER_RUN == 15
            assert settings.MAX_COMPUTE_MINUTES == 8
            assert len(settings.allowed_origins_list) == 2
    
    def test_development_settings(self):
        """Test development settings configuration."""
        dev_env = {
            'DEBUG': 'true',
            'HOST': '127.0.0.1',
            'PORT': '8001',
            'DATABASE_URL': 'sqlite:///./test.db',
            'REDIS_URL': 'redis://localhost:6379/1',
            'LOCAL_STORAGE_PATH': './dev_storage',
            'OPENAI_API_KEY': 'test-key',
            'ALLOWED_ORIGINS': 'http://localhost:3000,http://localhost:3001'
        }
        
        with patch.dict(os.environ, dev_env):
            settings = Settings()
            
            assert settings.DEBUG is True
            assert settings.HOST == "127.0.0.1"
            assert settings.PORT == 8001
            assert "sqlite" in settings.DATABASE_URL
            assert settings.LOCAL_STORAGE_PATH == "./dev_storage"
            assert len(settings.allowed_origins_list) == 2
    
    def test_minimal_settings(self):
        """Test minimal settings with only required fields."""
        with patch.dict(os.environ, {}, clear=True):
            settings = Settings()
            
            # Should work with all defaults
            assert settings.DEBUG is True
            assert settings.HOST == "0.0.0.0"
            assert settings.PORT == 8000
            assert settings.DATABASE_URL.startswith("sqlite")
            assert settings.REDIS_URL.startswith("redis")
            assert settings.LOCAL_STORAGE_PATH == "./local_s3"
            assert settings.OPENAI_API_KEY is None
            assert settings.ANTHROPIC_API_KEY is None
