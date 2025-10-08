"""
Metrics Operations Service

Core metrics calculations using pandas operations.
Each function takes a DataFrame and returns computed metrics.
"""

import pandas as pd
import numpy as np
from typing import Dict, Any, Optional, Union


class MetricsOperationsService:
    """Collection of metrics operations using pandas."""
    
    @staticmethod
    def percentile_time_to_threshold(
        df: pd.DataFrame, 
        threshold_pct: float,
        time_col: str = 't',
        value_col: str = 'v',
        group_by: Optional[str] = None
    ) -> Union[float, pd.Series]:
        """
        Find the time when a percentage threshold is reached.
        
        Args:
            df: DataFrame with time series data
            threshold_pct: Percentage threshold (0-100)
            time_col: Name of time column
            value_col: Name of value column
            group_by: Optional column to group by
            
        Returns:
            Time when threshold is reached (single value or Series if grouped)
        """
        if group_by:
            def find_threshold_time(group):
                threshold_rows = group[group[value_col] >= threshold_pct]
                return threshold_rows[time_col].min() if not threshold_rows.empty else np.nan
            
            return df.groupby(group_by).apply(find_threshold_time)
        else:
            threshold_rows = df[df[value_col] >= threshold_pct]
            return threshold_rows[time_col].min() if not threshold_rows.empty else np.nan
    
    @staticmethod
    def time_above_threshold(
        df: pd.DataFrame,
        threshold: float,
        time_col: str = 't',
        value_col: str = 'v',
        group_by: Optional[str] = None
    ) -> Union[float, pd.Series]:
        """
        Calculate total time spent above threshold.
        
        Args:
            df: DataFrame with time series data
            threshold: Threshold value
            time_col: Name of time column
            value_col: Name of value column
            group_by: Optional column to group by
            
        Returns:
            Total time above threshold (single value or Series if grouped)
        """
        if group_by:
            def calc_time_above(group):
                above_threshold = group[group[value_col] > threshold]
                if above_threshold.empty:
                    return 0.0
                
                # Calculate time differences
                time_diffs = above_threshold[time_col].diff().fillna(0)
                return time_diffs.sum()
            
            return df.groupby(group_by).apply(calc_time_above)
        else:
            above_threshold = df[df[value_col] > threshold]
            if above_threshold.empty:
                return 0.0
            
            # Calculate time differences
            time_diffs = above_threshold[time_col].diff().fillna(0)
            return time_diffs.sum()
    
    @staticmethod
    def max_value(
        df: pd.DataFrame,
        value_col: str = 'v',
        group_by: Optional[str] = None
    ) -> Union[float, pd.Series]:
        """
        Find maximum value.
        
        Args:
            df: DataFrame with data
            value_col: Name of value column
            group_by: Optional column to group by
            
        Returns:
            Maximum value (single value or Series if grouped)
        """
        if group_by:
            return df.groupby(group_by)[value_col].max()
        else:
            return df[value_col].max() if not df.empty else np.nan
    
    @staticmethod
    def min_value(
        df: pd.DataFrame,
        value_col: str = 'v',
        group_by: Optional[str] = None
    ) -> Union[float, pd.Series]:
        """
        Find minimum value.
        
        Args:
            df: DataFrame with data
            value_col: Name of value column
            group_by: Optional column to group by
            
        Returns:
            Minimum value (single value or Series if grouped)
        """
        if group_by:
            return df.groupby(group_by)[value_col].min()
        else:
            return df[value_col].min() if not df.empty else np.nan
    
    @staticmethod
    def mean_value(
        df: pd.DataFrame,
        value_col: str = 'v',
        group_by: Optional[str] = None
    ) -> Union[float, pd.Series]:
        """
        Calculate mean value.
        
        Args:
            df: DataFrame with data
            value_col: Name of value column
            group_by: Optional column to group by
            
        Returns:
            Mean value (single value or Series if grouped)
        """
        if group_by:
            return df.groupby(group_by)[value_col].mean()
        else:
            return df[value_col].mean() if not df.empty else np.nan
    
    @staticmethod
    def median_value(
        df: pd.DataFrame,
        value_col: str = 'v',
        group_by: Optional[str] = None
    ) -> Union[float, pd.Series]:
        """
        Calculate median value.
        
        Args:
            df: DataFrame with data
            value_col: Name of value column
            group_by: Optional column to group by
            
        Returns:
            Median value (single value or Series if grouped)
        """
        if group_by:
            return df.groupby(group_by)[value_col].median()
        else:
            return df[value_col].median() if not df.empty else np.nan
    
    @staticmethod
    def std_value(
        df: pd.DataFrame,
        value_col: str = 'v',
        group_by: Optional[str] = None
    ) -> Union[float, pd.Series]:
        """
        Calculate standard deviation.
        
        Args:
            df: DataFrame with data
            value_col: Name of value column
            group_by: Optional column to group by
            
        Returns:
            Standard deviation (single value or Series if grouped)
        """
        if group_by:
            return df.groupby(group_by)[value_col].std()
        else:
            return df[value_col].std() if not df.empty else np.nan
    
    @staticmethod
    def count_events(
        df: pd.DataFrame,
        group_by: Optional[str] = None
    ) -> Union[int, pd.Series]:
        """
        Count number of events/rows.
        
        Args:
            df: DataFrame with data
            group_by: Optional column to group by
            
        Returns:
            Count of events (single value or Series if grouped)
        """
        if group_by:
            return df.groupby(group_by).size()
        else:
            return len(df)
    
    @staticmethod
    def percentile_value(
        df: pd.DataFrame,
        percentile: float,
        value_col: str = 'v',
        group_by: Optional[str] = None
    ) -> Union[float, pd.Series]:
        """
        Calculate percentile value.
        
        Args:
            df: DataFrame with data
            percentile: Percentile to calculate (0-100)
            value_col: Name of value column
            group_by: Optional column to group by
            
        Returns:
            Percentile value (single value or Series if grouped)
        """
        if group_by:
            return df.groupby(group_by)[value_col].quantile(percentile / 100.0)
        else:
            return df[value_col].quantile(percentile / 100.0) if not df.empty else np.nan
    
    @staticmethod
    def sum_value(
        df: pd.DataFrame,
        value_col: str = 'v',
        group_by: Optional[str] = None
    ) -> Union[float, pd.Series]:
        """
        Calculate sum of values.
        
        Args:
            df: DataFrame with data
            value_col: Name of value column
            group_by: Optional column to group by
            
        Returns:
            Sum of values (single value or Series if grouped)
        """
        if group_by:
            return df.groupby(group_by)[value_col].sum()
        else:
            return df[value_col].sum() if not df.empty else 0.0
    
    @staticmethod
    def rate_of_change(
        df: pd.DataFrame,
        time_col: str = 't',
        value_col: str = 'v',
        group_by: Optional[str] = None
    ) -> Union[float, pd.Series]:
        """
        Calculate average rate of change.
        
        Args:
            df: DataFrame with time series data
            time_col: Name of time column
            value_col: Name of value column
            group_by: Optional column to group by
            
        Returns:
            Average rate of change (single value or Series if grouped)
        """
        if group_by:
            def calc_rate(group):
                if len(group) < 2:
                    return np.nan
                
                # Sort by time
                group_sorted = group.sort_values(time_col)
                
                # Calculate differences
                time_diff = group_sorted[time_col].diff()
                value_diff = group_sorted[value_col].diff()
                
                # Calculate rates (excluding first NaN)
                rates = (value_diff / time_diff).dropna()
                
                return rates.mean() if not rates.empty else np.nan
            
            return df.groupby(group_by).apply(calc_rate)
        else:
            if len(df) < 2:
                return np.nan
            
            # Sort by time
            df_sorted = df.sort_values(time_col)
            
            # Calculate differences
            time_diff = df_sorted[time_col].diff()
            value_diff = df_sorted[value_col].diff()
            
            # Calculate rates (excluding first NaN)
            rates = (value_diff / time_diff).dropna()
            
            return rates.mean() if not rates.empty else np.nan
    
    @staticmethod
    def time_to_peak(
        df: pd.DataFrame,
        time_col: str = 't',
        value_col: str = 'v',
        group_by: Optional[str] = None
    ) -> Union[float, pd.Series]:
        """
        Find time when peak value is reached.
        
        Args:
            df: DataFrame with time series data
            time_col: Name of time column
            value_col: Name of value column
            group_by: Optional column to group by
            
        Returns:
            Time to peak (single value or Series if grouped)
        """
        if group_by:
            def find_peak_time(group):
                if group.empty:
                    return np.nan
                
                peak_idx = group[value_col].idxmax()
                return group.loc[peak_idx, time_col]
            
            return df.groupby(group_by).apply(find_peak_time)
        else:
            if df.empty:
                return np.nan
            
            peak_idx = df[value_col].idxmax()
            return df.loc[peak_idx, time_col]
