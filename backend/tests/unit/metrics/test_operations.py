"""
Tests for metrics.operations module.
"""

import pytest
import pandas as pd
import numpy as np
from unittest.mock import Mock

from metrics.operations import MetricsOperations


class TestMetricsOperations:
    """Test the MetricsOperations class."""
    
    def setup_method(self):
        """Set up test data for each test."""
        # Create sample timeseries data
        self.timeseries_data = pd.DataFrame({
            't': [0, 60, 120, 180, 240, 300, 360, 420, 480, 540],
            'v': [0, 10, 25, 45, 70, 85, 95, 98, 99, 100],
            'scope': ['city'] * 10,
            'k': ['clearance_pct'] * 10
        })
        
        # Create sample queue data with multiple edges
        self.queue_data = pd.DataFrame({
            't': [0, 60, 120, 180, 240, 300] * 2,
            'v': [0, 5, 12, 8, 3, 0, 2, 8, 15, 10, 4, 1],
            'scope': ['edge:123'] * 6 + ['edge:456'] * 6,
            'k': ['queue_len'] * 12
        })
        
        # Create sample density data
        self.density_data = pd.DataFrame({
            't': [0, 60, 120, 180, 240, 300, 360, 420],
            'v': [2.0, 3.5, 4.2, 5.1, 4.8, 3.9, 2.5, 1.8],
            'scope': ['station_a'] * 8,
            'k': ['density'] * 8
        })
        
        self.ops = MetricsOperations()
    
    def test_percentile_time_to_threshold_single_group(self):
        """Test percentile time to threshold for single group."""
        # Test 95% threshold
        result = self.ops.percentile_time_to_threshold(
            self.timeseries_data, threshold_pct=95
        )
        assert result == 360  # Time when clearance reaches 95%
        
        # Test 50% threshold (should find closest value >= 50)
        result = self.ops.percentile_time_to_threshold(
            self.timeseries_data, threshold_pct=50
        )
        assert result == 180  # Time when clearance reaches 70% (first >= 50%)
        
        # Test 100% threshold
        result = self.ops.percentile_time_to_threshold(
            self.timeseries_data, threshold_pct=100
        )
        assert result == 540  # Time when clearance reaches 100%
    
    def test_percentile_time_to_threshold_with_grouping(self):
        """Test percentile time to threshold with grouping."""
        result = self.ops.percentile_time_to_threshold(
            self.queue_data, threshold_pct=10, group_by='scope'
        )
        
        assert isinstance(result, pd.Series)
        assert 'edge:123' in result.index
        assert 'edge:456' in result.index
        assert result['edge:123'] == 120  # First time edge:123 >= 10
        assert result['edge:456'] == 120  # First time edge:456 >= 10
    
    def test_percentile_time_to_threshold_not_reached(self):
        """Test percentile time to threshold when threshold is never reached."""
        result = self.ops.percentile_time_to_threshold(
            self.timeseries_data, threshold_pct=150  # Impossible threshold
        )
        assert pd.isna(result)
    
    def test_time_above_threshold_single_group(self):
        """Test time above threshold for single group."""
        result = self.ops.time_above_threshold(
            self.density_data, threshold=4.0
        )
        
        # Should count time when density > 4.0
        # From t=120 to t=240 (density: 4.2, 5.1, 4.8)
        # Time intervals: 60 + 60 = 120 seconds
        assert result == 120.0
    
    def test_time_above_threshold_with_grouping(self):
        """Test time above threshold with grouping."""
        result = self.ops.time_above_threshold(
            self.queue_data, threshold=5, group_by='scope'
        )
        
        assert isinstance(result, pd.Series)
        assert 'edge:123' in result.index
        assert 'edge:456' in result.index
        
        # edge:123 has values [0, 5, 12, 8, 3, 0] - above 5: 12, 8
        # Time intervals when above 5: 60 (from 120 to 180) + 60 (from 180 to 240) = 120
        assert result['edge:123'] == 120.0
        
        # edge:456 has values [2, 8, 15, 10, 4, 1] - above 5: 8, 15, 10
        # Time intervals when above 5: 60 + 60 + 60 = 180
        assert result['edge:456'] == 180.0
    
    def test_time_above_threshold_never_exceeded(self):
        """Test time above threshold when threshold is never exceeded."""
        result = self.ops.time_above_threshold(
            self.density_data, threshold=10.0  # Higher than any value
        )
        assert result == 0.0
    
    def test_max_value_single_group(self):
        """Test max value for single group."""
        result = self.ops.max_value(self.timeseries_data)
        assert result == 100
    
    def test_max_value_with_grouping(self):
        """Test max value with grouping."""
        result = self.ops.max_value(self.queue_data, group_by='scope')
        
        assert isinstance(result, pd.Series)
        assert result['edge:123'] == 12
        assert result['edge:456'] == 15
    
    def test_min_value_single_group(self):
        """Test min value for single group."""
        result = self.ops.min_value(self.timeseries_data)
        assert result == 0
    
    def test_min_value_with_grouping(self):
        """Test min value with grouping."""
        result = self.ops.min_value(self.queue_data, group_by='scope')
        
        assert isinstance(result, pd.Series)
        assert result['edge:123'] == 0
        assert result['edge:456'] == 1
    
    def test_quantile_single_group(self):
        """Test quantile calculation for single group."""
        # Test median (50th percentile)
        result = self.ops.quantile(self.timeseries_data, q=0.5)
        expected_median = self.timeseries_data['v'].quantile(0.5)
        assert result == expected_median
        
        # Test 95th percentile
        result = self.ops.quantile(self.timeseries_data, q=0.95)
        expected_95th = self.timeseries_data['v'].quantile(0.95)
        assert result == expected_95th
    
    def test_quantile_with_grouping(self):
        """Test quantile calculation with grouping."""
        result = self.ops.quantile(self.queue_data, q=0.5, group_by='scope')
        
        assert isinstance(result, pd.Series)
        assert 'edge:123' in result.index
        assert 'edge:456' in result.index
        
        # Verify against pandas groupby quantile
        expected = self.queue_data.groupby('scope')['v'].quantile(0.5)
        pd.testing.assert_series_equal(result, expected)
    
    def test_value_at_time_exact_match(self):
        """Test value at time with exact time match."""
        result = self.ops.value_at_time(self.timeseries_data, target_time=180)
        assert result == 45  # Value at t=180
    
    def test_value_at_time_interpolation(self):
        """Test value at time with interpolation (closest before)."""
        result = self.ops.value_at_time(self.timeseries_data, target_time=150)
        assert result == 25  # Value at t=120 (closest before 150)
    
    def test_value_at_time_with_grouping(self):
        """Test value at time with grouping."""
        result = self.ops.value_at_time(
            self.queue_data, target_time=150, group_by='scope'
        )
        
        assert isinstance(result, pd.Series)
        assert 'edge:123' in result.index
        assert 'edge:456' in result.index
        
        # Should return values at t=120 for both groups (closest before 150)
        assert result['edge:123'] == 12
        assert result['edge:456'] == 15
    
    def test_value_at_time_before_start(self):
        """Test value at time before any data points."""
        result = self.ops.value_at_time(self.timeseries_data, target_time=-100)
        assert pd.isna(result)
    
    def test_area_under_curve_single_group(self):
        """Test area under curve calculation."""
        # Create simple test data for known AUC
        simple_data = pd.DataFrame({
            't': [0, 1, 2],
            'v': [0, 1, 0]
        })
        
        result = self.ops.area_under_curve(simple_data)
        assert result == 1.0  # Triangle with base=2, height=1, area=1
    
    def test_area_under_curve_with_grouping(self):
        """Test area under curve with grouping."""
        result = self.ops.area_under_curve(self.queue_data, group_by='scope')
        
        assert isinstance(result, pd.Series)
        assert 'edge:123' in result.index
        assert 'edge:456' in result.index
        
        # Results should be positive (area under curve)
        assert result['edge:123'] > 0
        assert result['edge:456'] > 0
    
    def test_area_under_curve_insufficient_data(self):
        """Test area under curve with insufficient data points."""
        single_point = pd.DataFrame({'t': [0], 'v': [5]})
        result = self.ops.area_under_curve(single_point)
        assert result == 0.0
    
    def test_mean_value_single_group(self):
        """Test mean value calculation."""
        result = self.ops.mean_value(self.timeseries_data)
        expected = self.timeseries_data['v'].mean()
        assert result == expected
    
    def test_mean_value_with_grouping(self):
        """Test mean value with grouping."""
        result = self.ops.mean_value(self.queue_data, group_by='scope')
        
        assert isinstance(result, pd.Series)
        expected = self.queue_data.groupby('scope')['v'].mean()
        pd.testing.assert_series_equal(result, expected)
    
    def test_count_events_single_group(self):
        """Test count events for single group."""
        result = self.ops.count_events(self.timeseries_data)
        assert result == len(self.timeseries_data)
    
    def test_count_events_with_grouping(self):
        """Test count events with grouping."""
        result = self.ops.count_events(self.queue_data, group_by='scope')
        
        assert isinstance(result, pd.Series)
        assert result['edge:123'] == 6
        assert result['edge:456'] == 6
    
    def test_custom_column_names(self):
        """Test operations with custom column names."""
        custom_data = pd.DataFrame({
            'time': [0, 10, 20, 30],
            'measurement': [1, 2, 3, 4],
            'category': ['A', 'A', 'B', 'B']
        })
        
        # Test max value with custom column names
        result = self.ops.max_value(
            custom_data, 
            value_col='measurement', 
            group_by='category'
        )
        
        assert isinstance(result, pd.Series)
        assert result['A'] == 2
        assert result['B'] == 4
        
        # Test percentile time to threshold with custom column names
        result = self.ops.percentile_time_to_threshold(
            custom_data,
            threshold_pct=2.5,
            time_col='time',
            value_col='measurement',
            group_by='category'
        )
        
        assert isinstance(result, pd.Series)
        assert result['B'] == 20  # First time category B >= 2.5
    
    def test_empty_dataframe(self):
        """Test operations with empty DataFrame."""
        empty_df = pd.DataFrame(columns=['t', 'v', 'scope'])
        
        # Most operations should handle empty data gracefully
        result = self.ops.max_value(empty_df)
        assert pd.isna(result)
        
        result = self.ops.count_events(empty_df)
        assert result == 0
        
        result = self.ops.percentile_time_to_threshold(empty_df, threshold_pct=50)
        assert pd.isna(result)
    
    def test_single_row_dataframe(self):
        """Test operations with single row DataFrame."""
        single_row = pd.DataFrame({
            't': [100],
            'v': [50],
            'scope': ['test']
        })
        
        result = self.ops.max_value(single_row)
        assert result == 50
        
        result = self.ops.percentile_time_to_threshold(single_row, threshold_pct=40)
        assert result == 100
        
        result = self.ops.area_under_curve(single_row)
        assert result == 0.0  # Need at least 2 points for AUC
    
    def test_nan_handling(self):
        """Test handling of NaN values in data."""
        data_with_nan = pd.DataFrame({
            't': [0, 60, 120, 180],
            'v': [10, np.nan, 30, 40],
            'scope': ['test'] * 4
        })
        
        # Max should ignore NaN
        result = self.ops.max_value(data_with_nan)
        assert result == 40
        
        # Mean should ignore NaN
        result = self.ops.mean_value(data_with_nan)
        expected = data_with_nan['v'].mean()  # pandas mean ignores NaN
        assert result == expected
    
    def test_duplicate_times(self):
        """Test handling of duplicate time values."""
        duplicate_times = pd.DataFrame({
            't': [0, 60, 60, 120],  # Duplicate at t=60
            'v': [10, 20, 25, 30],
            'scope': ['test'] * 4
        })
        
        # Should handle duplicates gracefully
        result = self.ops.max_value(duplicate_times)
        assert result == 30
        
        result = self.ops.percentile_time_to_threshold(duplicate_times, threshold_pct=22)
        assert result == 60  # First occurrence of value >= 22


@pytest.mark.unit
class TestMetricsOperationsEdgeCases:
    """Test edge cases and error conditions."""
    
    def test_invalid_threshold_percentages(self):
        """Test with invalid threshold percentages."""
        data = pd.DataFrame({'t': [0, 1], 'v': [10, 20]})
        ops = MetricsOperations()
        
        # Negative threshold should work (just won't find matches)
        result = ops.percentile_time_to_threshold(data, threshold_pct=-10)
        assert result == 0  # First value is >= -10
        
        # Very high threshold
        result = ops.percentile_time_to_threshold(data, threshold_pct=1000)
        assert pd.isna(result)
    
    def test_invalid_quantile_values(self):
        """Test with invalid quantile values."""
        data = pd.DataFrame({'t': [0, 1], 'v': [10, 20]})
        ops = MetricsOperations()
        
        # pandas will handle invalid quantiles, but let's test edge cases
        result = ops.quantile(data, q=0.0)  # 0th percentile (minimum)
        assert result == 10
        
        result = ops.quantile(data, q=1.0)  # 100th percentile (maximum)
        assert result == 20
    
    def test_unsorted_time_data(self):
        """Test with unsorted time data."""
        unsorted_data = pd.DataFrame({
            't': [120, 0, 240, 60],  # Unsorted times
            'v': [30, 10, 40, 20],
            'scope': ['test'] * 4
        })
        
        ops = MetricsOperations()
        
        # Operations that sort internally should work correctly
        result = ops.time_above_threshold(unsorted_data, threshold=15)
        # Should sort and calculate correctly
        assert result > 0
        
        result = ops.area_under_curve(unsorted_data)
        # Should sort and calculate AUC correctly
        assert result > 0
    
    def test_missing_columns(self):
        """Test behavior with missing expected columns."""
        data = pd.DataFrame({'time': [0, 1], 'value': [10, 20]})
        ops = MetricsOperations()
        
        # Should raise KeyError for missing default columns
        with pytest.raises(KeyError):
            ops.max_value(data)  # Missing 'v' column
        
        # Should work with custom column names
        result = ops.max_value(data, value_col='value')
        assert result == 20
    
    def test_all_same_values(self):
        """Test with all identical values."""
        same_values = pd.DataFrame({
            't': [0, 60, 120, 180],
            'v': [50, 50, 50, 50],  # All same
            'scope': ['test'] * 4
        })
        
        ops = MetricsOperations()
        
        result = ops.max_value(same_values)
        assert result == 50
        
        result = ops.min_value(same_values)
        assert result == 50
        
        result = ops.quantile(same_values, q=0.5)
        assert result == 50
        
        result = ops.percentile_time_to_threshold(same_values, threshold_pct=50)
        assert result == 0  # First time point meets threshold
    
    def test_large_dataset_performance(self):
        """Test with larger dataset to ensure reasonable performance."""
        # Create larger dataset
        n_points = 10000
        large_data = pd.DataFrame({
            't': range(n_points),
            'v': np.random.rand(n_points) * 100,
            'scope': ['group_' + str(i % 10) for i in range(n_points)]
        })
        
        ops = MetricsOperations()
        
        # These should complete without timeout
        result = ops.max_value(large_data, group_by='scope')
        assert isinstance(result, pd.Series)
        assert len(result) == 10  # 10 groups
        
        result = ops.mean_value(large_data, group_by='scope')
        assert isinstance(result, pd.Series)
        assert len(result) == 10
