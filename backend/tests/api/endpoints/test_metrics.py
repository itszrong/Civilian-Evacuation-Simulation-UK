"""
Tests for api.metrics module.
"""

import pytest
import pandas as pd
import tempfile
import shutil
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
from fastapi.testclient import TestClient

from api.metrics import router, MetricRequest, MetricsRequest
from core.config import Settings


class TestMetricsAPI:
    """Test metrics API endpoints."""
    
    def setup_method(self):
        """Set up test environment."""
        self.temp_dir = tempfile.mkdtemp()
        
        # Create test settings
        self.test_settings = Settings(
            DEBUG=True,
            LOCAL_STORAGE_PATH=self.temp_dir
        )
        
        # Create test data
        self.create_test_data()
    
    def teardown_method(self):
        """Clean up test environment."""
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def create_test_data(self):
        """Create test data files."""
        runs_dir = Path(self.temp_dir) / "runs"
        runs_dir.mkdir(exist_ok=True)
        
        # Create timeseries data
        timeseries_df = pd.DataFrame({
            'run_id': ['test_run'] * 10,
            't': list(range(0, 600, 60)),  # 10 minutes
            'k': ['clearance_pct'] * 10,
            'scope': ['city'] * 10,
            'v': [i * 10 for i in range(10)]  # 0, 10, 20, ..., 90
        })
        
        # Create events data
        events_df = pd.DataFrame({
            'run_id': ['test_run'] * 3,
            't': [0, 180, 540],
            'type': ['start', 'warning', 'end'],
            'id': ['sim_start', 'warn_1', 'sim_end'],
            'attrs': ['{}', '{"severity": "high"}', '{}']
        })
        
        # Save to parquet files
        timeseries_path = runs_dir / "timeseries_test_run.parquet"
        events_path = runs_dir / "events_test_run.parquet"
        
        timeseries_df.to_parquet(timeseries_path)
        events_df.to_parquet(events_path)
    
    @pytest.fixture
    def client(self):
        """Create test client."""
        from fastapi import FastAPI
        app = FastAPI()
        app.include_router(router)
        return TestClient(app)
    
    def test_get_available_metrics_success(self, client):
        """Test successful retrieval of available metrics."""
        with patch('api.metrics.get_settings', return_value=self.test_settings):
            response = client.get("/metrics/test_run/available")
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["run_id"] == "test_run"
        assert data["timeseries"]["available"] is True
        assert data["timeseries"]["row_count"] == 10
        assert "clearance_pct" in data["timeseries"]["metric_keys"]
        assert data["events"]["available"] is True
        assert data["events"]["row_count"] == 3
        assert "warning" in data["events"]["event_types"]
    
    def test_get_available_metrics_nonexistent_run(self, client):
        """Test available metrics for nonexistent run."""
        with patch('api.metrics.get_settings', return_value=self.test_settings):
            response = client.get("/metrics/nonexistent_run/available")
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["run_id"] == "nonexistent_run"
        assert data["timeseries"]["available"] is False
        assert data["timeseries"]["row_count"] == 0
        assert data["events"]["available"] is False
        assert data["events"]["row_count"] == 0
    
    def test_calculate_single_metric_success(self, client):
        """Test successful single metric calculation."""
        request_data = {
            "run_id": "test_run",
            "source": "timeseries",
            "metric_key": "clearance_pct",
            "operation": "max_value",
            "filters": {"scope": "city"}
        }
        
        with patch('api.metrics.get_settings', return_value=self.test_settings):
            response = client.post("/metrics/calculate", json=request_data)
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["metric_name"] == "calculated_metric"
        assert data["value"] == 90  # Max value in test data
        assert data["error"] is None
    
    def test_calculate_single_metric_with_args(self, client):
        """Test single metric calculation with operation arguments."""
        request_data = {
            "run_id": "test_run",
            "source": "timeseries",
            "metric_key": "clearance_pct",
            "operation": "percentile_time_to_threshold",
            "args": {"threshold_pct": 50},
            "filters": {"scope": "city"}
        }
        
        with patch('api.metrics.get_settings', return_value=self.test_settings):
            response = client.post("/metrics/calculate", json=request_data)
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["value"] == 300  # Time when value reaches 50
        assert data["error"] is None
    
    def test_calculate_single_metric_with_post_processing(self, client):
        """Test single metric calculation with post-processing."""
        request_data = {
            "run_id": "test_run",
            "source": "timeseries",
            "metric_key": "clearance_pct",
            "operation": "percentile_time_to_threshold",
            "args": {"threshold_pct": 50},
            "filters": {"scope": "city"},
            "post_process": {"divide_by": 60, "round_to": 1}  # Convert to minutes
        }
        
        with patch('api.metrics.get_settings', return_value=self.test_settings):
            response = client.post("/metrics/calculate", json=request_data)
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["value"] == 5.0  # 300 seconds / 60 = 5 minutes
        assert data["error"] is None
    
    def test_calculate_single_metric_events(self, client):
        """Test single metric calculation for events data."""
        request_data = {
            "run_id": "test_run",
            "source": "events",
            "operation": "count_events",
            "filters": {"type": "warning"}
        }
        
        with patch('api.metrics.get_settings', return_value=self.test_settings):
            response = client.post("/metrics/calculate", json=request_data)
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["value"] == 1  # One warning event
        assert data["error"] is None
    
    def test_calculate_single_metric_error(self, client):
        """Test single metric calculation with error."""
        request_data = {
            "run_id": "test_run",
            "source": "invalid_source",
            "operation": "max_value"
        }
        
        with patch('api.metrics.get_settings', return_value=self.test_settings):
            response = client.post("/metrics/calculate", json=request_data)
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["error"] is not None
        assert "Unknown source" in data["error"]
    
    def test_calculate_single_metric_missing_metric_key(self, client):
        """Test single metric calculation without required metric_key."""
        request_data = {
            "run_id": "test_run",
            "source": "timeseries",
            "operation": "max_value"
            # Missing metric_key
        }
        
        with patch('api.metrics.get_settings', return_value=self.test_settings):
            response = client.post("/metrics/calculate", json=request_data)
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["error"] is not None
        assert "metric_key is required" in data["error"]
    
    def test_calculate_multiple_metrics_success(self, client):
        """Test successful multiple metrics calculation."""
        request_data = {
            "run_id": "test_run",
            "metrics": {
                "max_clearance": {
                    "source": "timeseries",
                    "metric_key": "clearance_pct",
                    "operation": "max_value",
                    "filters": {"scope": "city"}
                },
                "total_events": {
                    "source": "events",
                    "operation": "count_events"
                },
                "clearance_p50_minutes": {
                    "source": "timeseries",
                    "metric_key": "clearance_pct",
                    "operation": "percentile_time_to_threshold",
                    "args": {"threshold_pct": 50},
                    "filters": {"scope": "city"},
                    "post_process": {"divide_by": 60, "round_to": 1}
                }
            }
        }
        
        with patch('api.metrics.get_settings', return_value=self.test_settings):
            response = client.post("/metrics/calculate-multiple", json=request_data)
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["run_id"] == "test_run"
        assert "results" in data
        
        results = data["results"]
        assert "max_clearance" in results
        assert "total_events" in results
        assert "clearance_p50_minutes" in results
        
        assert results["max_clearance"] == 90
        assert results["total_events"] == 3
        assert results["clearance_p50_minutes"] == 5.0
    
    def test_calculate_multiple_metrics_with_errors(self, client):
        """Test multiple metrics calculation with some errors."""
        request_data = {
            "run_id": "test_run",
            "metrics": {
                "valid_metric": {
                    "source": "timeseries",
                    "metric_key": "clearance_pct",
                    "operation": "max_value"
                },
                "invalid_metric": {
                    "source": "invalid_source",
                    "operation": "invalid_operation"
                }
            }
        }
        
        with patch('api.metrics.get_settings', return_value=self.test_settings):
            response = client.post("/metrics/calculate-multiple", json=request_data)
        
        assert response.status_code == 200
        data = response.json()
        
        results = data["results"]
        assert "valid_metric" in results
        assert "invalid_metric" in results
        
        assert results["valid_metric"] == 90
        assert isinstance(results["invalid_metric"], dict)
        assert "error" in results["invalid_metric"]
    
    def test_calculate_multiple_metrics_nonexistent_run(self, client):
        """Test multiple metrics calculation for nonexistent run."""
        request_data = {
            "run_id": "nonexistent_run",
            "metrics": {
                "test_metric": {
                    "source": "timeseries",
                    "metric_key": "clearance_pct",
                    "operation": "max_value"
                }
            }
        }
        
        with patch('api.metrics.get_settings', return_value=self.test_settings):
            response = client.post("/metrics/calculate-multiple", json=request_data)
        
        assert response.status_code == 200
        data = response.json()
        
        results = data["results"]
        assert "test_metric" in results
        assert isinstance(results["test_metric"], dict)
        assert "error" in results["test_metric"]
    
    def test_get_run_timeseries_success(self, client):
        """Test successful retrieval of run timeseries data."""
        with patch('api.metrics.get_settings', return_value=self.test_settings):
            response = client.get("/metrics/test_run/timeseries")
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["run_id"] == "test_run"
        assert data["row_count"] == 10
        assert len(data["data"]) == 10
        
        # Check first row
        first_row = data["data"][0]
        assert first_row["t"] == 0
        assert first_row["k"] == "clearance_pct"
        assert first_row["scope"] == "city"
        assert first_row["v"] == 0
    
    def test_get_run_timeseries_with_filters(self, client):
        """Test retrieval of run timeseries data with filters."""
        with patch('api.metrics.get_settings', return_value=self.test_settings):
            response = client.get("/metrics/test_run/timeseries?t_min=180&t_max=360")
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["row_count"] == 4  # 4 rows in time range
        assert all(row["t"] >= 180 and row["t"] <= 360 for row in data["data"])
    
    def test_get_run_timeseries_nonexistent_run(self, client):
        """Test retrieval of timeseries data for nonexistent run."""
        with patch('api.metrics.get_settings', return_value=self.test_settings):
            response = client.get("/metrics/nonexistent_run/timeseries")
        
        assert response.status_code == 404
        data = response.json()
        assert "not found" in data["detail"].lower()
    
    def test_get_run_events_success(self, client):
        """Test successful retrieval of run events data."""
        with patch('api.metrics.get_settings', return_value=self.test_settings):
            response = client.get("/metrics/test_run/events")
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["run_id"] == "test_run"
        assert data["row_count"] == 3
        assert len(data["data"]) == 3
        
        # Check first event
        first_event = data["data"][0]
        assert first_event["t"] == 0
        assert first_event["type"] == "start"
        assert first_event["id"] == "sim_start"
    
    def test_get_run_events_with_filters(self, client):
        """Test retrieval of run events data with filters."""
        with patch('api.metrics.get_settings', return_value=self.test_settings):
            response = client.get("/metrics/test_run/events?type=warning")
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["row_count"] == 1  # Only warning events
        assert data["data"][0]["type"] == "warning"
    
    def test_get_run_events_nonexistent_run(self, client):
        """Test retrieval of events data for nonexistent run."""
        with patch('api.metrics.get_settings', return_value=self.test_settings):
            response = client.get("/metrics/nonexistent_run/events")
        
        assert response.status_code == 404
        data = response.json()
        assert "not found" in data["detail"].lower()
    
    def test_invalid_request_data(self, client):
        """Test API with invalid request data."""
        # Missing required fields
        invalid_request = {
            "run_id": "test_run"
            # Missing source and operation
        }
        
        response = client.post("/metrics/calculate", json=invalid_request)
        assert response.status_code == 422  # Validation error
    
    def test_empty_metrics_request(self, client):
        """Test multiple metrics calculation with empty metrics dict."""
        request_data = {
            "run_id": "test_run",
            "metrics": {}
        }
        
        with patch('api.metrics.get_settings', return_value=self.test_settings):
            response = client.post("/metrics/calculate-multiple", json=request_data)
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["run_id"] == "test_run"
        assert data["results"] == {}


@pytest.mark.integration
class TestMetricsAPIIntegration:
    """Integration tests for metrics API."""
    
    def test_metrics_api_in_full_app(self, client):
        """Test metrics API in full application context."""
        # This would test the API with real data and dependencies
        response = client.get("/api/metrics/sample_run/available")
        
        # Should return either 200 with data or 404 if run doesn't exist
        assert response.status_code in [200, 404]
        
        if response.status_code == 200:
            data = response.json()
            assert "run_id" in data
            assert "timeseries" in data
            assert "events" in data
    
    def test_calculate_metric_end_to_end(self, client):
        """Test end-to-end metric calculation."""
        # This test would use real sample data if available
        request_data = {
            "run_id": "sample_run",
            "source": "timeseries",
            "metric_key": "clearance_pct",
            "operation": "max_value"
        }
        
        response = client.post("/api/metrics/calculate", json=request_data)
        
        # Should handle gracefully whether data exists or not
        assert response.status_code == 200
        data = response.json()
        
        # Either successful calculation or error message
        assert "value" in data or "error" in data


class TestMetricsAPIModels:
    """Test Pydantic models for metrics API."""
    
    def test_metric_request_model(self):
        """Test MetricRequest model validation."""
        # Valid request
        valid_data = {
            "run_id": "test_run",
            "source": "timeseries",
            "metric_key": "clearance_pct",
            "operation": "max_value",
            "filters": {"scope": "city"},
            "post_process": {"divide_by": 60}
        }
        
        request = MetricRequest(**valid_data)
        assert request.run_id == "test_run"
        assert request.source == "timeseries"
        assert request.metric_key == "clearance_pct"
        assert request.operation == "max_value"
        assert request.filters == {"scope": "city"}
        assert request.post_process == {"divide_by": 60}
    
    def test_metric_request_defaults(self):
        """Test MetricRequest model with default values."""
        minimal_data = {
            "run_id": "test_run",
            "operation": "count_events"
        }
        
        request = MetricRequest(**minimal_data)
        assert request.run_id == "test_run"
        assert request.source == "timeseries"  # Default
        assert request.metric_key is None
        assert request.operation == "count_events"
        assert request.args == {}
        assert request.filters == {}
        assert request.group_by is None
        assert request.post_process == {}
    
    def test_metrics_request_model(self):
        """Test MetricsRequest model validation."""
        valid_data = {
            "run_id": "test_run",
            "metrics": {
                "metric1": {
                    "source": "timeseries",
                    "metric_key": "clearance_pct",
                    "operation": "max_value"
                },
                "metric2": {
                    "source": "events",
                    "operation": "count_events"
                }
            }
        }
        
        request = MetricsRequest(**valid_data)
        assert request.run_id == "test_run"
        assert len(request.metrics) == 2
        assert "metric1" in request.metrics
        assert "metric2" in request.metrics
    
    def test_metrics_request_empty_metrics(self):
        """Test MetricsRequest with empty metrics dict."""
        data = {
            "run_id": "test_run",
            "metrics": {}
        }
        
        request = MetricsRequest(**data)
        assert request.run_id == "test_run"
        assert request.metrics == {}
    
    def test_metric_request_validation_errors(self):
        """Test MetricRequest validation errors."""
        from pydantic import ValidationError
        
        # Missing required field
        with pytest.raises(ValidationError):
            MetricRequest(operation="max_value")  # Missing run_id
        
        # Invalid data types
        with pytest.raises(ValidationError):
            MetricRequest(
                run_id="test_run",
                operation="max_value",
                args="invalid_args"  # Should be dict
            )
