"""
Tests for api.health module.
"""

import pytest
import os
import tempfile
import shutil
from unittest.mock import Mock, patch, MagicMock
from fastapi.testclient import TestClient

from api.health import router
from core.config import Settings


class TestHealthEndpoints:
    """Test health check endpoints."""
    
    def setup_method(self):
        """Set up test environment."""
        self.temp_dir = tempfile.mkdtemp()
        
        # Create test settings
        self.test_settings = Settings(
            DEBUG=True,
            LOCAL_STORAGE_PATH=self.temp_dir,
            OPENAI_API_KEY="test-openai-key",
            ANTHROPIC_API_KEY="test-anthropic-key"
        )
    
    def teardown_method(self):
        """Clean up test environment."""
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    @pytest.fixture
    def client(self):
        """Create test client."""
        from fastapi import FastAPI
        app = FastAPI()
        app.include_router(router)
        return TestClient(app)
    
    def test_health_check_success(self, client):
        """Test successful health check."""
        with patch('api.health.get_settings', return_value=self.test_settings):
            response = client.get("/health")
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["status"] == "healthy"
        assert "timestamp" in data
        assert data["service"] == "London Evacuation Planning Tool"
        assert data["version"] == "1.0.0"
    
    def test_readiness_check_all_ready(self, client):
        """Test readiness check when all services are ready."""
        # Mock all dependencies to be ready
        with patch('api.health.get_settings', return_value=self.test_settings), \
             patch('api.health.feed_service') as mock_feed_service, \
             patch('api.health.LondonGraphService') as mock_graph_service:
            
            # Mock feed service config
            mock_config = Mock()
            mock_config.tiers = [Mock(sources=[Mock(), Mock()])]  # 2 sources in 1 tier
            mock_feed_service.config = mock_config
            
            # Mock graph service initialization
            mock_graph_service.return_value = Mock()
            
            response = client.get("/ready")
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["status"] == "ready"
        assert "timestamp" in data
        assert "checks" in data
        
        checks = data["checks"]
        assert "storage" in checks
        assert "sources_config" in checks
        assert "ai_services" in checks
        assert "simulation" in checks
        
        # All checks should be ready
        assert checks["storage"]["status"] == "ready"
        assert checks["sources_config"]["status"] == "ready"
        assert checks["ai_services"]["status"] == "ready"
        assert checks["simulation"]["status"] == "ready"
    
    def test_readiness_check_storage_not_ready(self, client):
        """Test readiness check when storage is not accessible."""
        # Use non-existent directory
        bad_settings = Settings(
            DEBUG=True,
            LOCAL_STORAGE_PATH="/nonexistent/path",
            OPENAI_API_KEY="test-key"
        )
        
        with patch('api.health.get_settings', return_value=bad_settings), \
             patch('api.health.feed_service') as mock_feed_service, \
             patch('api.health.LondonGraphService') as mock_graph_service:
            
            mock_config = Mock()
            mock_config.tiers = [Mock(sources=[Mock()])]
            mock_feed_service.config = mock_config
            mock_graph_service.return_value = Mock()
            
            response = client.get("/ready")
        
        assert response.status_code == 503  # Service Unavailable
        data = response.json()
        
        assert data["status"] == "not_ready"
        assert data["checks"]["storage"]["status"] == "not_ready"
        assert "error" in data["checks"]["storage"]
    
    def test_readiness_check_sources_config_error(self, client):
        """Test readiness check when sources config has errors."""
        with patch('api.health.get_settings', return_value=self.test_settings), \
             patch('api.health.feed_service') as mock_feed_service, \
             patch('api.health.LondonGraphService') as mock_graph_service:
            
            # Mock feed service to raise exception
            mock_feed_service.config = Mock(side_effect=Exception("Config error"))
            mock_graph_service.return_value = Mock()
            
            response = client.get("/ready")
        
        assert response.status_code == 503
        data = response.json()
        
        assert data["status"] == "not_ready"
        assert data["checks"]["sources_config"]["status"] == "not_ready"
        assert "Config error" in data["checks"]["sources_config"]["error"]
    
    def test_readiness_check_no_ai_keys(self, client):
        """Test readiness check when no AI API keys are configured."""
        no_ai_settings = Settings(
            DEBUG=True,
            LOCAL_STORAGE_PATH=self.temp_dir,
            OPENAI_API_KEY=None,
            ANTHROPIC_API_KEY=None
        )
        
        with patch('api.health.get_settings', return_value=no_ai_settings), \
             patch('api.health.feed_service') as mock_feed_service, \
             patch('api.health.LondonGraphService') as mock_graph_service:
            
            mock_config = Mock()
            mock_config.tiers = [Mock(sources=[Mock()])]
            mock_feed_service.config = mock_config
            mock_graph_service.return_value = Mock()
            
            response = client.get("/ready")
        
        # Should still be ready (AI services are optional)
        assert response.status_code == 200
        data = response.json()
        
        assert data["status"] == "ready"
        assert data["checks"]["ai_services"]["status"] == "not_ready"
        assert "No AI API keys configured" in data["checks"]["ai_services"]["error"]
    
    def test_readiness_check_simulation_error(self, client):
        """Test readiness check when simulation service fails."""
        with patch('api.health.get_settings', return_value=self.test_settings), \
             patch('api.health.feed_service') as mock_feed_service, \
             patch('api.health.LondonGraphService', side_effect=Exception("Simulation error")):
            
            mock_config = Mock()
            mock_config.tiers = [Mock(sources=[Mock()])]
            mock_feed_service.config = mock_config
            
            response = client.get("/ready")
        
        assert response.status_code == 503
        data = response.json()
        
        assert data["status"] == "not_ready"
        assert data["checks"]["simulation"]["status"] == "not_ready"
        assert "Simulation error" in data["checks"]["simulation"]["error"]
    
    def test_system_metrics_success(self, client):
        """Test successful system metrics collection."""
        # Create mock run directories and files
        runs_dir = os.path.join(self.temp_dir, "runs")
        os.makedirs(runs_dir)
        
        # Create successful run
        success_run_dir = os.path.join(runs_dir, "run_001")
        os.makedirs(success_run_dir)
        scenarios_dir = os.path.join(success_run_dir, "scenarios")
        os.makedirs(scenarios_dir)
        
        # Create memo file
        memo_path = os.path.join(success_run_dir, "memo.json")
        with open(memo_path, 'w') as f:
            f.write('{"justification": {"abstained": false}}')
        
        # Create scenario files
        for i in range(3):
            scenario_path = os.path.join(scenarios_dir, f"scenario_{i}.yml")
            with open(scenario_path, 'w') as f:
                f.write(f"id: scenario_{i}")
        
        # Create failed run
        failed_run_dir = os.path.join(runs_dir, "run_002")
        os.makedirs(failed_run_dir)
        # No memo file = failed run
        
        with patch('api.health.storage_service') as mock_storage, \
             patch('api.health.feed_service') as mock_feed_service:
            
            mock_storage.settings.LOCAL_STORAGE_PATH = self.temp_dir
            mock_feed_service.get_ingestion_status.return_value = {
                "last_global_refresh": "2023-01-01T00:00:00Z",
                "total_documents": 100
            }
            
            response = client.get("/system-metrics")
        
        assert response.status_code == 200
        data = response.json()
        
        assert "timestamp" in data
        assert "metrics" in data
        
        metrics = data["metrics"]
        assert metrics["runs_total"] == 2
        assert metrics["runs_successful"] == 1
        assert metrics["runs_failed"] == 1
        assert metrics["scenarios_simulated_total"] == 3
        assert metrics["abstain_rate"] == 0.0  # No abstains
        assert metrics["success_rate"] == 0.5  # 1/2 successful
        assert metrics["feeds_total_documents"] == 100
    
    def test_system_metrics_with_abstains(self, client):
        """Test system metrics with abstained explanations."""
        runs_dir = os.path.join(self.temp_dir, "runs")
        os.makedirs(runs_dir)
        
        # Create run with abstained explanation
        run_dir = os.path.join(runs_dir, "run_001")
        os.makedirs(run_dir)
        
        memo_path = os.path.join(run_dir, "memo.json")
        with open(memo_path, 'w') as f:
            f.write('{"justification": {"abstained": true}}')
        
        with patch('api.health.storage_service') as mock_storage, \
             patch('api.health.feed_service') as mock_feed_service:
            
            mock_storage.settings.LOCAL_STORAGE_PATH = self.temp_dir
            mock_feed_service.get_ingestion_status.return_value = {
                "total_documents": 50
            }
            
            response = client.get("/system-metrics")
        
        assert response.status_code == 200
        data = response.json()
        
        metrics = data["metrics"]
        assert metrics["abstain_rate"] == 1.0  # 1 abstain out of 1 total
    
    def test_system_metrics_no_runs_directory(self, client):
        """Test system metrics when runs directory doesn't exist."""
        with patch('api.health.storage_service') as mock_storage, \
             patch('api.health.feed_service') as mock_feed_service:
            
            mock_storage.settings.LOCAL_STORAGE_PATH = self.temp_dir
            mock_feed_service.get_ingestion_status.return_value = {}
            
            response = client.get("/system-metrics")
        
        assert response.status_code == 200
        data = response.json()
        
        metrics = data["metrics"]
        assert metrics["runs_total"] == 0
        assert metrics["runs_successful"] == 0
        assert metrics["runs_failed"] == 0
        assert metrics["scenarios_simulated_total"] == 0
    
    def test_system_metrics_exception_handling(self, client):
        """Test system metrics exception handling."""
        with patch('api.health.feed_service') as mock_feed_service:
            # Mock feed service to raise exception
            mock_feed_service.get_ingestion_status.side_effect = Exception("Feed service error")
            
            response = client.get("/system-metrics")
        
        assert response.status_code == 200
        data = response.json()
        
        assert "metrics" in data
        assert "error" in data["metrics"]
        assert "Feed service error" in data["metrics"]["error"]
    
    def test_system_metrics_corrupted_memo_file(self, client):
        """Test system metrics with corrupted memo file."""
        runs_dir = os.path.join(self.temp_dir, "runs")
        os.makedirs(runs_dir)
        
        run_dir = os.path.join(runs_dir, "run_001")
        os.makedirs(run_dir)
        
        # Create corrupted memo file
        memo_path = os.path.join(run_dir, "memo.json")
        with open(memo_path, 'w') as f:
            f.write('invalid json content')
        
        with patch('api.health.storage_service') as mock_storage, \
             patch('api.health.feed_service') as mock_feed_service:
            
            mock_storage.settings.LOCAL_STORAGE_PATH = self.temp_dir
            mock_feed_service.get_ingestion_status.return_value = {}
            
            response = client.get("/system-metrics")
        
        assert response.status_code == 200
        data = response.json()
        
        # Should handle corrupted file gracefully
        metrics = data["metrics"]
        assert metrics["runs_total"] == 1
        assert metrics["runs_successful"] == 1  # File exists, so counted as successful
        assert metrics["abstain_rate"] == 0.0  # Couldn't parse, so no abstains counted


@pytest.mark.integration
class TestHealthEndpointsIntegration:
    """Integration tests for health endpoints."""
    
    def test_health_endpoint_in_full_app(self, client):
        """Test health endpoint in full application context."""
        response = client.get("/api/health")
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["status"] == "healthy"
        assert data["service"] == "London Evacuation Planning Tool"
    
    def test_readiness_endpoint_in_full_app(self, client):
        """Test readiness endpoint in full application context."""
        response = client.get("/api/ready")
        
        # Should return either 200 or 503 depending on system state
        assert response.status_code in [200, 503]
        data = response.json()
        
        assert data["status"] in ["ready", "not_ready"]
        assert "checks" in data
    
    def test_system_metrics_endpoint_in_full_app(self, client):
        """Test system metrics endpoint in full application context."""
        response = client.get("/api/system-metrics")
        
        assert response.status_code == 200
        data = response.json()
        
        assert "timestamp" in data
        assert "metrics" in data
        
        # Should have basic metrics structure
        metrics = data["metrics"]
        assert "runs_total" in metrics
        assert "runs_successful" in metrics
        assert "runs_failed" in metrics
