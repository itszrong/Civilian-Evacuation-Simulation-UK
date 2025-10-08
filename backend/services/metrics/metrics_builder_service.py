"""
Metrics Builder Service

Main class for building and executing metrics on simulation data.
Uses simple YAML/dict configuration and pandas operations.
"""

import pandas as pd
import numpy as np
from pathlib import Path
from typing import Dict, Any, List, Optional, Union
import yaml
import json

from .metrics_operations_service import MetricsOperationsService

try:
    from evaluation.evaluator import FrameworkEvaluator
    EVALUATOR_AVAILABLE = True
except ImportError:
    EVALUATOR_AVAILABLE = False
    FrameworkEvaluator = None


class MetricsBuilderService:
    """Simple metrics builder using pandas operations."""
    
    def __init__(self, data_path: Optional[str] = None):
        """
        Initialize metrics builder.
        
        Args:
            data_path: Optional path to data directory
        """
        self.data_path = Path(data_path) if data_path else None
        self.operations = MetricsOperationsService()
        self._cached_data: Dict[str, pd.DataFrame] = {}
        self.evaluator = FrameworkEvaluator() if EVALUATOR_AVAILABLE else None
    
    def load_timeseries_data(self, run_id: str) -> pd.DataFrame:
        """
        Load timeseries data for a run.
        
        Args:
            run_id: Simulation run ID
            
        Returns:
            DataFrame with timeseries data
        """
        cache_key = f"timeseries_{run_id}"
        if cache_key in self._cached_data:
            return self._cached_data[cache_key]
        
        # Try different possible file locations
        possible_paths = []
        if self.data_path:
            possible_paths.extend([
                self.data_path / "results" / f"{run_id}_timeseries.jsonl",
                self.data_path / "runs" / run_id / "timeseries.jsonl",
                self.data_path / f"{run_id}_timeseries.jsonl"
            ])
        
        # Default paths
        possible_paths.extend([
            Path("local_s3/results") / f"{run_id}_timeseries.jsonl",
            Path("backend/local_s3/results") / f"{run_id}_timeseries.jsonl",
            Path(f"{run_id}_timeseries.jsonl")
        ])
        
        df = None
        for path in possible_paths:
            if path.exists():
                try:
                    # Load JSONL file
                    records = []
                    with open(path, 'r') as f:
                        for line in f:
                            if line.strip():
                                records.append(json.loads(line))
                    
                    if records:
                        df = pd.DataFrame(records)
                        break
                except Exception as e:
                    print(f"Failed to load {path}: {e}")
                    continue
        
        if df is None:
            print(f"No timeseries data found for run {run_id}")
            df = pd.DataFrame()
        
        self._cached_data[cache_key] = df
        return df
    
    def load_events_data(self, run_id: str) -> pd.DataFrame:
        """
        Load events data for a run.
        
        Args:
            run_id: Simulation run ID
            
        Returns:
            DataFrame with events data
        """
        cache_key = f"events_{run_id}"
        if cache_key in self._cached_data:
            return self._cached_data[cache_key]
        
        # Try different possible file locations
        possible_paths = []
        if self.data_path:
            possible_paths.extend([
                self.data_path / "results" / f"{run_id}_events.jsonl",
                self.data_path / "runs" / run_id / "events.jsonl",
                self.data_path / f"{run_id}_events.jsonl"
            ])
        
        # Default paths
        possible_paths.extend([
            Path("local_s3/results") / f"{run_id}_events.jsonl",
            Path("backend/local_s3/results") / f"{run_id}_events.jsonl",
            Path(f"{run_id}_events.jsonl")
        ])
        
        df = None
        for path in possible_paths:
            if path.exists():
                try:
                    # Load JSONL file
                    records = []
                    with open(path, 'r') as f:
                        for line in f:
                            if line.strip():
                                records.append(json.loads(line))
                    
                    if records:
                        df = pd.DataFrame(records)
                        break
                except Exception as e:
                    print(f"Failed to load {path}: {e}")
                    continue
        
        if df is None:
            print(f"No events data found for run {run_id}")
            df = pd.DataFrame()
        
        self._cached_data[cache_key] = df
        return df
    
    def calculate_metrics(
        self, 
        run_id: str, 
        metrics_config: Union[Dict[str, Any], str, Path]
    ) -> Dict[str, Any]:
        """
        Calculate metrics for a run using configuration.
        
        Args:
            run_id: Simulation run ID
            metrics_config: Metrics configuration (dict or path to config file)
            
        Returns:
            Dictionary of calculated metrics
        """
        # Load configuration
        if isinstance(metrics_config, (str, Path)):
            config_path = Path(metrics_config)
            if not config_path.exists():
                # Try relative to data path
                if self.data_path:
                    config_path = self.data_path / metrics_config
                if not config_path.exists():
                    raise FileNotFoundError(f"Metrics config file not found: {metrics_config}")
            
            with open(config_path, 'r') as f:
                if config_path.suffix.lower() in ['.yml', '.yaml']:
                    config = yaml.safe_load(f)
                else:
                    config = json.load(f)
        else:
            config = metrics_config
        
        results = {}
        
        # Calculate individual metrics
        if 'metrics' in config:
            for metric_name, metric_config in config['metrics'].items():
                try:
                    result = self._calculate_single_metric(run_id, metric_config)
                    results[metric_name] = result
                except Exception as e:
                    print(f"Failed to calculate metric {metric_name}: {e}")
                    results[metric_name] = None
        
        # Calculate grouped metrics
        if 'grouped_metrics' in config:
            for metric_name, metric_config in config['grouped_metrics'].items():
                try:
                    result = self._calculate_grouped_metric(run_id, metric_config)
                    results[metric_name] = result
                except Exception as e:
                    print(f"Failed to calculate grouped metric {metric_name}: {e}")
                    results[metric_name] = None
        
        return results
    
    def _calculate_single_metric(self, run_id: str, metric_config: Dict[str, Any]) -> Any:
        """Calculate a single metric."""
        source = metric_config.get('source', 'timeseries')
        
        # Load appropriate data
        if source == 'timeseries':
            df = self.load_timeseries_data(run_id)
        elif source == 'events':
            df = self.load_events_data(run_id)
        else:
            raise ValueError(f"Unknown data source: {source}")
        
        if df.empty:
            return None
        
        # Apply filters
        filtered_df = self._apply_filters(df, metric_config.get('filters', {}))
        
        if filtered_df.empty:
            return None
        
        # Get the specific metric data
        metric_key = metric_config.get('metric_key')
        if metric_key and metric_key in filtered_df.columns:
            # Use specific column
            data_df = filtered_df[['t', metric_key]].rename(columns={metric_key: 'v'})
        else:
            # Use all data
            data_df = filtered_df
        
        # Apply operation
        operation = metric_config.get('operation')
        operation_args = metric_config.get('args', {})
        
        if hasattr(self.operations, operation):
            operation_func = getattr(self.operations, operation)
            result = operation_func(data_df, **operation_args)
        else:
            raise ValueError(f"Unknown operation: {operation}")
        
        # Post-process result
        if 'post_process' in metric_config:
            result = self._post_process_result(result, metric_config['post_process'])
        
        return result
    
    def _calculate_grouped_metric(self, run_id: str, metric_config: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate a grouped metric."""
        source = metric_config.get('source', 'timeseries')
        
        # Load appropriate data
        if source == 'timeseries':
            df = self.load_timeseries_data(run_id)
        elif source == 'events':
            df = self.load_events_data(run_id)
        else:
            raise ValueError(f"Unknown data source: {source}")
        
        if df.empty:
            return {}
        
        # Apply filters
        filtered_df = self._apply_filters(df, metric_config.get('filters', {}))
        
        if filtered_df.empty:
            return {}
        
        # Group by specified column
        group_by = metric_config.get('group_by')
        if not group_by or group_by not in filtered_df.columns:
            raise ValueError(f"Group by column not found: {group_by}")
        
        # Get the specific metric data
        metric_key = metric_config.get('metric_key')
        if metric_key and metric_key in filtered_df.columns:
            # Use specific column
            data_df = filtered_df[['t', metric_key, group_by]].rename(columns={metric_key: 'v'})
        else:
            # Use all data
            data_df = filtered_df
        
        # Apply operation to each group
        operation = metric_config.get('operation')
        operation_args = metric_config.get('args', {})
        
        if hasattr(self.operations, operation):
            operation_func = getattr(self.operations, operation)
            
            results = {}
            for group_name, group_df in data_df.groupby(group_by):
                try:
                    result = operation_func(group_df, **operation_args)
                    
                    # Post-process result
                    if 'post_process' in metric_config:
                        result = self._post_process_result(result, metric_config['post_process'])
                    
                    results[str(group_name)] = result
                except Exception as e:
                    print(f"Failed to calculate metric for group {group_name}: {e}")
                    results[str(group_name)] = None
            
            return results
        else:
            raise ValueError(f"Unknown operation: {operation}")
    
    def _apply_filters(self, df: pd.DataFrame, filters: Dict[str, Any]) -> pd.DataFrame:
        """Apply filters to dataframe."""
        filtered_df = df.copy()
        
        for filter_key, filter_value in filters.items():
            if filter_key == 'scope' and 'scope' in filtered_df.columns:
                filtered_df = filtered_df[filtered_df['scope'] == filter_value]
            elif filter_key == 'scope_contains' and 'scope' in filtered_df.columns:
                filtered_df = filtered_df[filtered_df['scope'].str.contains(filter_value, na=False)]
            elif filter_key == 'type' and 'type' in filtered_df.columns:
                filtered_df = filtered_df[filtered_df['type'] == filter_value]
            elif filter_key in filtered_df.columns:
                filtered_df = filtered_df[filtered_df[filter_key] == filter_value]
        
        return filtered_df
    
    def _post_process_result(self, result: Any, post_process_config: Dict[str, Any]) -> Any:
        """Apply post-processing to result."""
        if result is None:
            return result
        
        # Handle pandas Series
        if isinstance(result, pd.Series):
            if 'divide_by' in post_process_config:
                result = result / post_process_config['divide_by']
            if 'round_to' in post_process_config:
                result = result.round(post_process_config['round_to'])
            return result.to_dict()
        
        # Handle scalar values
        if 'divide_by' in post_process_config:
            result = result / post_process_config['divide_by']
        if 'round_to' in post_process_config:
            result = round(result, post_process_config['round_to'])
        
        return result
    
    def get_available_metrics(self, run_id: str) -> Dict[str, List[str]]:
        """
        Get available metrics for a run.
        
        Args:
            run_id: Simulation run ID
            
        Returns:
            Dictionary with available columns for each data source
        """
        available = {}
        
        # Check timeseries data
        timeseries_df = self.load_timeseries_data(run_id)
        if not timeseries_df.empty:
            available['timeseries'] = list(timeseries_df.columns)
        
        # Check events data
        events_df = self.load_events_data(run_id)
        if not events_df.empty:
            available['events'] = list(events_df.columns)
        
        return available
    
    def clear_cache(self):
        """Clear cached data."""
        self._cached_data.clear()
    
    def validate_config(self, config: Dict[str, Any]) -> List[str]:
        """
        Validate metrics configuration.
        
        Args:
            config: Metrics configuration
            
        Returns:
            List of validation errors (empty if valid)
        """
        errors = []
        
        if 'metrics' in config:
            for metric_name, metric_config in config['metrics'].items():
                errors.extend(self._validate_metric_config(metric_name, metric_config))
        
        if 'grouped_metrics' in config:
            for metric_name, metric_config in config['grouped_metrics'].items():
                errors.extend(self._validate_metric_config(metric_name, metric_config, grouped=True))
        
        return errors
    
    def _validate_metric_config(self, metric_name: str, config: Dict[str, Any], grouped: bool = False) -> List[str]:
        """Validate a single metric configuration."""
        errors = []
        
        # Check required fields
        if 'operation' not in config:
            errors.append(f"{metric_name}: Missing required field 'operation'")
        elif not hasattr(self.operations, config['operation']):
            errors.append(f"{metric_name}: Unknown operation '{config['operation']}'")
        
        if 'source' in config and config['source'] not in ['timeseries', 'events']:
            errors.append(f"{metric_name}: Invalid source '{config['source']}', must be 'timeseries' or 'events'")
        
        if grouped and 'group_by' not in config:
            errors.append(f"{metric_name}: Grouped metrics must specify 'group_by'")
        
        return errors
