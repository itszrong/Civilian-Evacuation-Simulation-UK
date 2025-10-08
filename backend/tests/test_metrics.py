"""
Tests for the simple metrics builder.
"""

import pytest
import pandas as pd
import numpy as np
from pathlib import Path
import tempfile
import os

from services.metrics.metrics_builder_service import MetricsBuilderService
from services.metrics.metrics_operations_service import MetricsOperationsServiceService


class TestMetricsOperationsService:
    """Test the core metrics operations."""
    
    def setup_method(self):
        """Set up test data."""
        # Create sample timeseries data
        self.timeseries_data = pd.DataFrame({
            't': [0, 60, 120, 180, 240, 300, 360, 420, 480, 540],
            'v': [0, 10, 25, 45, 70, 85, 95, 98, 99, 100],
            'scope': ['city'] * 10,
            'k': ['clearance_pct'] * 10
        })
        
        # Create sample queue data
        self.queue_data = pd.DataFrame({
            't': [0, 60, 120, 180, 240, 300],
            'v': [0, 5, 12, 8, 3, 0],
            'scope': ['edge:123', 'edge:123', 'edge:123', 'edge:456', 'edge:456', 'edge:456'],
            'k': ['queue_len'] * 6
        })
        
        self.ops = MetricsOperationsService()
    
    def test_percentile_time_to_threshold(self):
        """Test percentile time to threshold calculation."""
        # Test 95% threshold
        result = self.ops.percentile_time_to_threshold(
            self.timeseries_data, threshold_pct=95
        )
        assert result == 360  # Time when clearance reaches 95%
        
        # Test 50% threshold
        result = self.ops.percentile_time_to_threshold(
            self.timeseries_data, threshold_pct=50
        )
        assert result == 180  # Time when clearance reaches 45% (closest to 50%)
    
    def test_time_above_threshold(self):
        """Test time above threshold calculation."""
        result = self.ops.time_above_threshold(
            self.queue_data, threshold=5
        )
        # Should count time when queue > 5: from t=120 to t=180 (60 seconds)
        assert result == 60
    
    def test_max_value(self):
        """Test max value calculation."""
        result = self.ops.max_value(self.timeseries_data)
        assert result == 100
        
        # Test with grouping
        result = self.ops.max_value(self.queue_data, group_by='scope')
        assert isinstance(result, pd.Series)
        assert result['edge:123'] == 12
        assert result['edge:456'] == 8
    
    def test_quantile(self):
        """Test quantile calculation."""
        result = self.ops.quantile(self.timeseries_data, q=0.5)
        assert result == 77.5  # Median of the values
    
    def test_area_under_curve(self):
        """Test area under curve calculation."""
        # Simple test with known values
        simple_data = pd.DataFrame({
            't': [0, 1, 2],
            'v': [0, 1, 0]
        })
        result = self.ops.area_under_curve(simple_data)
        assert result == 1.0  # Triangle with base=2, height=1


class TestMetricsBuilderService:
    """Test the metrics builder."""
    
    def setup_method(self):
        """Set up test environment."""
        self.temp_dir = tempfile.mkdtemp()
        self.builder = MetricsBuilderService(self.temp_dir)
        
        # Create test data files
        self.create_test_data()
    
    def teardown_method(self):
        """Clean up test environment."""
        import shutil
        shutil.rmtree(self.temp_dir)
    
    def create_test_data(self):
        """Create test data files."""
        # Timeseries data
        timeseries_df = pd.DataFrame({
            'run_id': ['test_run'] * 10,
            't': [0, 60, 120, 180, 240, 300, 360, 420, 480, 540],
            'k': ['clearance_pct'] * 10,
            'scope': ['city'] * 10,
            'v': [0, 10, 25, 45, 70, 85, 95, 98, 99, 100]
        })
        
        timeseries_path = Path(self.temp_dir) / "timeseries_test_run.parquet"
        timeseries_df.to_parquet(timeseries_path)
        
        # Events data
        events_df = pd.DataFrame({
            'run_id': ['test_run'] * 3,
            't': [0, 120, 300],
            'type': ['start', 'emergency', 'end'],
            'id': ['sim_start', 'fire_alarm', 'sim_end'],
            'attrs': ['{}', '{"location": "building_a"}', '{}']
        })
        
        events_path = Path(self.temp_dir) / "events_test_run.parquet"
        events_df.to_parquet(events_path)
    
    def test_load_data(self):
        """Test data loading."""
        # Test timeseries loading
        df = self.builder.load_timeseries_data('test_run')
        assert not df.empty
        assert len(df) == 10
        assert 'clearance_pct' in df['k'].values
        
        # Test events loading
        df = self.builder.load_events_data('test_run')
        assert not df.empty
        assert len(df) == 3
        assert 'emergency' in df['type'].values
    
    def test_calculate_metric(self):
        """Test single metric calculation."""
        metric_config = {
            'source': 'timeseries',
            'metric_key': 'clearance_pct',
            'operation': 'percentile_time_to_threshold',
            'args': {'threshold_pct': 95},
            'filters': {'scope': 'city'},
            'post_process': {'divide_by': 60, 'round_to': 1}
        }
        
        result = self.builder.calculate_metric('test_run', metric_config)
        assert result == 6.0  # 360 seconds / 60 = 6 minutes
    
    def test_calculate_metrics_from_dict(self):
        """Test multiple metrics calculation from dictionary."""
        metrics_config = {
            'metrics': {
                'clearance_p95': {
                    'source': 'timeseries',
                    'metric_key': 'clearance_pct',
                    'operation': 'percentile_time_to_threshold',
                    'args': {'threshold_pct': 95},
                    'post_process': {'divide_by': 60, 'round_to': 1}
                },
                'total_events': {
                    'source': 'events',
                    'operation': 'count_events'
                }
            }
        }
        
        results = self.builder.calculate_metrics('test_run', metrics_config)
        
        assert 'clearance_p95' in results
        assert 'total_events' in results
        assert results['clearance_p95'] == 6.0
        assert results['total_events'] == 3
    
    def test_get_available_metrics(self):
        """Test getting available metrics info."""
        info = self.builder.get_available_metrics('test_run')
        
        assert info['run_id'] == 'test_run'
        assert info['timeseries']['available'] is True
        assert info['timeseries']['row_count'] == 10
        assert 'clearance_pct' in info['timeseries']['metric_keys']
        assert info['events']['available'] is True
        assert info['events']['row_count'] == 3
        assert 'emergency' in info['events']['event_types']
    
    def test_filters(self):
        """Test data filtering."""
        metric_config = {
            'source': 'timeseries',
            'metric_key': 'clearance_pct',
            'operation': 'max_value',
            'filters': {'t_min': 180, 't_max': 360}  # Only middle portion
        }
        
        result = self.builder.calculate_metric('test_run', metric_config)
        assert result == 95  # Max value in the filtered time range
    
    def test_nonexistent_run(self):
        """Test handling of nonexistent run."""
        info = self.builder.get_available_metrics('nonexistent_run')
        
        assert info['timeseries']['available'] is False
        assert info['timeseries']['row_count'] == 0
        assert info['events']['available'] is False
        assert info['events']['row_count'] == 0


if __name__ == "__main__":
    pytest.main([__file__])
