"""
Unified Error Handler Service
Provides consistent error handling patterns across all services with proper logging and user feedback.
"""

import traceback
import uuid
from datetime import datetime
from typing import Dict, Any, Optional, Union, Callable
from enum import Enum
import structlog
from dataclasses import dataclass
from pathlib import Path
import json

logger = structlog.get_logger(__name__)


class ErrorSeverity(Enum):
    """Error severity levels for classification and handling."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ErrorCategory(Enum):
    """Error categories for better organization and handling."""
    VALIDATION = "validation"
    NETWORK = "network"
    SIMULATION = "simulation"
    GRAPH_LOADING = "graph_loading"
    DATA_PROCESSING = "data_processing"
    AUTHENTICATION = "authentication"
    AUTHORIZATION = "authorization"
    SYSTEM = "system"
    EXTERNAL_API = "external_api"
    UNKNOWN = "unknown"


@dataclass
class ErrorContext:
    """Context information for error handling."""
    
    error_id: str
    timestamp: str
    service_name: str
    operation_name: str
    user_id: Optional[str] = None
    request_id: Optional[str] = None
    additional_data: Optional[Dict[str, Any]] = None


@dataclass
class StandardError:
    """Standardized error structure for consistent handling."""
    
    error_id: str
    error_code: str
    message: str
    user_message: str
    severity: ErrorSeverity
    category: ErrorCategory
    context: ErrorContext
    technical_details: Optional[str] = None
    suggested_actions: Optional[list] = None
    retry_after: Optional[int] = None  # Seconds to wait before retry
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for API responses."""
        return {
            "error_id": self.error_id,
            "error_code": self.error_code,
            "message": self.message,
            "user_message": self.user_message,
            "severity": self.severity.value,
            "category": self.category.value,
            "timestamp": self.context.timestamp,
            "suggested_actions": self.suggested_actions or [],
            "retry_after": self.retry_after
        }
    
    def to_user_dict(self) -> Dict[str, Any]:
        """Convert to user-friendly dictionary (no technical details)."""
        return {
            "error_id": self.error_id,
            "message": self.user_message,
            "severity": self.severity.value,
            "suggested_actions": self.suggested_actions or [],
            "retry_after": self.retry_after
        }


class ErrorHandler:
    """
    Unified error handler for consistent error management across all services.
    Provides logging, user feedback, and error tracking capabilities.
    """
    
    def __init__(self, service_name: str, log_dir: Optional[str] = None):
        """
        Initialize error handler for a specific service.
        
        Args:
            service_name: Name of the service using this error handler
            log_dir: Directory for error logs (optional)
        """
        self.service_name = service_name
        self.log_dir = Path(log_dir) if log_dir else Path("backend/logs/errors")
        self.log_dir.mkdir(parents=True, exist_ok=True)
        
        # Error tracking
        self.error_history = []
        self.error_counts = {}
        
        # Error code mappings
        self.error_codes = {
            # Validation errors
            "INVALID_INPUT": {
                "category": ErrorCategory.VALIDATION,
                "severity": ErrorSeverity.MEDIUM,
                "user_message": "The provided input is invalid. Please check your data and try again.",
                "suggested_actions": ["Verify input format", "Check required fields", "Consult documentation"]
            },
            "MISSING_REQUIRED_FIELD": {
                "category": ErrorCategory.VALIDATION,
                "severity": ErrorSeverity.MEDIUM,
                "user_message": "Required information is missing. Please provide all necessary fields.",
                "suggested_actions": ["Check required fields", "Review input format"]
            },
            
            # Network errors
            "NETWORK_TIMEOUT": {
                "category": ErrorCategory.NETWORK,
                "severity": ErrorSeverity.HIGH,
                "user_message": "The operation timed out. Please try again in a few moments.",
                "suggested_actions": ["Retry the operation", "Check network connection"],
                "retry_after": 30
            },
            "CONNECTION_FAILED": {
                "category": ErrorCategory.NETWORK,
                "severity": ErrorSeverity.HIGH,
                "user_message": "Unable to connect to the service. Please try again later.",
                "suggested_actions": ["Check network connection", "Try again later"],
                "retry_after": 60
            },
            
            # Simulation errors
            "SIMULATION_FAILED": {
                "category": ErrorCategory.SIMULATION,
                "severity": ErrorSeverity.HIGH,
                "user_message": "The simulation could not be completed. Please check your parameters and try again.",
                "suggested_actions": ["Verify simulation parameters", "Try with different settings", "Contact support if issue persists"]
            },
            "INSUFFICIENT_DATA": {
                "category": ErrorCategory.SIMULATION,
                "severity": ErrorSeverity.MEDIUM,
                "user_message": "Insufficient data to run the simulation. Please provide more information.",
                "suggested_actions": ["Add more data points", "Check data completeness"]
            },
            
            # Graph loading errors
            "GRAPH_LOAD_FAILED": {
                "category": ErrorCategory.GRAPH_LOADING,
                "severity": ErrorSeverity.HIGH,
                "user_message": "Unable to load the street network. Please try a different location or try again later.",
                "suggested_actions": ["Try a different city", "Check if the location is supported", "Try again later"],
                "retry_after": 120
            },
            "UNSUPPORTED_CITY": {
                "category": ErrorCategory.GRAPH_LOADING,
                "severity": ErrorSeverity.MEDIUM,
                "user_message": "The selected city is not currently supported. Please choose from the available cities.",
                "suggested_actions": ["Select a supported city", "Check the list of available locations"]
            },
            
            # System errors
            "SYSTEM_OVERLOAD": {
                "category": ErrorCategory.SYSTEM,
                "severity": ErrorSeverity.CRITICAL,
                "user_message": "The system is currently experiencing high load. Please try again in a few minutes.",
                "suggested_actions": ["Wait and try again", "Try during off-peak hours"],
                "retry_after": 300
            },
            "RESOURCE_EXHAUSTED": {
                "category": ErrorCategory.SYSTEM,
                "severity": ErrorSeverity.CRITICAL,
                "user_message": "System resources are temporarily unavailable. Please try again later.",
                "suggested_actions": ["Try again later", "Contact support if issue persists"],
                "retry_after": 600
            },
            
            # Generic errors
            "UNKNOWN_ERROR": {
                "category": ErrorCategory.UNKNOWN,
                "severity": ErrorSeverity.HIGH,
                "user_message": "An unexpected error occurred. Please try again or contact support.",
                "suggested_actions": ["Try again", "Contact support with error ID"]
            }
        }
        
        logger.info(f"Error handler initialized for service: {service_name}")

    def handle_error(
        self,
        error: Union[Exception, str],
        error_code: Optional[str] = None,
        operation_name: str = "unknown_operation",
        user_id: Optional[str] = None,
        request_id: Optional[str] = None,
        additional_data: Optional[Dict[str, Any]] = None,
        custom_user_message: Optional[str] = None
    ) -> StandardError:
        """
        Handle an error with consistent logging and user feedback.
        
        Args:
            error: Exception or error message
            error_code: Predefined error code for classification
            operation_name: Name of the operation that failed
            user_id: ID of the user (if applicable)
            request_id: Request ID for tracking
            additional_data: Additional context data
            custom_user_message: Custom user-friendly message
            
        Returns:
            StandardError object with all error details
        """
        # Generate unique error ID
        error_id = str(uuid.uuid4())
        
        # Create error context
        context = ErrorContext(
            error_id=error_id,
            timestamp=datetime.now().isoformat(),
            service_name=self.service_name,
            operation_name=operation_name,
            user_id=user_id,
            request_id=request_id,
            additional_data=additional_data
        )
        
        # Determine error details
        if isinstance(error, Exception):
            error_message = str(error)
            technical_details = traceback.format_exc()
            
            # Try to infer error code from exception type
            if error_code is None:
                error_code = self._infer_error_code(error)
        else:
            error_message = str(error)
            technical_details = None
            error_code = error_code or "UNKNOWN_ERROR"
        
        # Get error configuration
        error_config = self.error_codes.get(error_code, self.error_codes["UNKNOWN_ERROR"])
        
        # Create standardized error
        standard_error = StandardError(
            error_id=error_id,
            error_code=error_code,
            message=error_message,
            user_message=custom_user_message or error_config["user_message"],
            severity=error_config["severity"],
            category=error_config["category"],
            context=context,
            technical_details=technical_details,
            suggested_actions=error_config.get("suggested_actions"),
            retry_after=error_config.get("retry_after")
        )
        
        # Log the error
        self._log_error(standard_error)
        
        # Track error statistics
        self._track_error(standard_error)
        
        # Store error for history
        self.error_history.append(standard_error)
        
        return standard_error

    def _infer_error_code(self, error: Exception) -> str:
        """Infer error code from exception type."""
        error_type = type(error).__name__
        
        # Map common exception types to error codes
        type_mappings = {
            "ValueError": "INVALID_INPUT",
            "KeyError": "MISSING_REQUIRED_FIELD",
            "TimeoutError": "NETWORK_TIMEOUT",
            "ConnectionError": "CONNECTION_FAILED",
            "FileNotFoundError": "INSUFFICIENT_DATA",
            "MemoryError": "RESOURCE_EXHAUSTED",
            "OSError": "SYSTEM_ERROR"
        }
        
        return type_mappings.get(error_type, "UNKNOWN_ERROR")

    def _log_error(self, error: StandardError):
        """Log error with appropriate level based on severity."""
        log_data = {
            "error_id": error.error_id,
            "error_code": error.error_code,
            "message": error.message,
            "severity": error.severity.value,
            "category": error.category.value,
            "service": self.service_name,
            "operation": error.context.operation_name,
            "user_id": error.context.user_id,
            "request_id": error.context.request_id
        }
        
        if error.severity == ErrorSeverity.CRITICAL:
            logger.critical("Critical error occurred", **log_data, technical_details=error.technical_details)
        elif error.severity == ErrorSeverity.HIGH:
            logger.error("High severity error occurred", **log_data, technical_details=error.technical_details)
        elif error.severity == ErrorSeverity.MEDIUM:
            logger.warning("Medium severity error occurred", **log_data)
        else:
            logger.info("Low severity error occurred", **log_data)
        
        # Write to error log file for critical and high severity errors
        if error.severity in [ErrorSeverity.CRITICAL, ErrorSeverity.HIGH]:
            self._write_error_log(error)

    def _write_error_log(self, error: StandardError):
        """Write detailed error log to file."""
        try:
            log_file = self.log_dir / f"errors_{datetime.now().strftime('%Y%m%d')}.json"
            
            error_log_entry = {
                "timestamp": error.context.timestamp,
                "error_id": error.error_id,
                "service": self.service_name,
                "error_code": error.error_code,
                "message": error.message,
                "severity": error.severity.value,
                "category": error.category.value,
                "operation": error.context.operation_name,
                "user_id": error.context.user_id,
                "request_id": error.context.request_id,
                "technical_details": error.technical_details,
                "additional_data": error.context.additional_data
            }
            
            # Append to daily log file
            with open(log_file, 'a') as f:
                f.write(json.dumps(error_log_entry) + '\n')
                
        except Exception as e:
            logger.warning(f"Failed to write error log: {e}")

    def _track_error(self, error: StandardError):
        """Track error statistics for monitoring."""
        error_key = f"{error.category.value}:{error.error_code}"
        
        if error_key not in self.error_counts:
            self.error_counts[error_key] = {
                "count": 0,
                "first_occurrence": error.context.timestamp,
                "last_occurrence": error.context.timestamp,
                "severity": error.severity.value
            }
        
        self.error_counts[error_key]["count"] += 1
        self.error_counts[error_key]["last_occurrence"] = error.context.timestamp

    def get_error_statistics(self) -> Dict[str, Any]:
        """Get error statistics for monitoring and analysis."""
        total_errors = len(self.error_history)
        
        if total_errors == 0:
            return {"message": "No errors recorded"}
        
        # Count by severity
        severity_counts = {}
        category_counts = {}
        
        for error in self.error_history:
            severity = error.severity.value
            category = error.category.value
            
            severity_counts[severity] = severity_counts.get(severity, 0) + 1
            category_counts[category] = category_counts.get(category, 0) + 1
        
        # Recent errors (last 24 hours)
        recent_errors = [
            error for error in self.error_history[-100:]  # Last 100 errors
        ]
        
        return {
            "summary": {
                "total_errors": total_errors,
                "recent_errors": len(recent_errors),
                "service": self.service_name
            },
            "by_severity": severity_counts,
            "by_category": category_counts,
            "error_counts": self.error_counts,
            "recent_errors": [
                {
                    "error_id": error.error_id,
                    "error_code": error.error_code,
                    "severity": error.severity.value,
                    "category": error.category.value,
                    "timestamp": error.context.timestamp,
                    "operation": error.context.operation_name
                }
                for error in recent_errors[-10:]  # Last 10 errors
            ]
        }

    def create_api_response(self, error: StandardError, include_technical: bool = False) -> Dict[str, Any]:
        """
        Create API response from standardized error.
        
        Args:
            error: StandardError object
            include_technical: Whether to include technical details
            
        Returns:
            API response dictionary
        """
        response = error.to_dict() if include_technical else error.to_user_dict()
        
        # Add service context
        response["service"] = self.service_name
        response["operation"] = error.context.operation_name
        
        return response

    def wrap_operation(self, operation_name: str, error_code: Optional[str] = None):
        """
        Decorator to wrap operations with consistent error handling.
        
        Args:
            operation_name: Name of the operation
            error_code: Default error code for this operation
            
        Returns:
            Decorator function
        """
        def decorator(func: Callable):
            async def async_wrapper(*args, **kwargs):
                try:
                    return await func(*args, **kwargs)
                except Exception as e:
                    error = self.handle_error(
                        error=e,
                        error_code=error_code,
                        operation_name=operation_name,
                        additional_data={"args": str(args), "kwargs": str(kwargs)}
                    )
                    # Return error response instead of raising
                    return {"error": error.to_user_dict()}
            
            def sync_wrapper(*args, **kwargs):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    error = self.handle_error(
                        error=e,
                        error_code=error_code,
                        operation_name=operation_name,
                        additional_data={"args": str(args), "kwargs": str(kwargs)}
                    )
                    # Return error response instead of raising
                    return {"error": error.to_user_dict()}
            
            # Return appropriate wrapper based on function type
            import asyncio
            if asyncio.iscoroutinefunction(func):
                return async_wrapper
            else:
                return sync_wrapper
        
        return decorator


# Global error handlers for different services
_error_handlers = {}

def get_error_handler(service_name: str) -> ErrorHandler:
    """Get or create error handler for a service."""
    if service_name not in _error_handlers:
        _error_handlers[service_name] = ErrorHandler(service_name)
    return _error_handlers[service_name]


# Convenience decorators for common services
def handle_simulation_errors(operation_name: str):
    """Decorator for simulation operations."""
    return get_error_handler("simulation").wrap_operation(operation_name, "SIMULATION_FAILED")

def handle_graph_errors(operation_name: str):
    """Decorator for graph operations."""
    return get_error_handler("graph_manager").wrap_operation(operation_name, "GRAPH_LOAD_FAILED")

def handle_api_errors(operation_name: str):
    """Decorator for API operations."""
    return get_error_handler("api").wrap_operation(operation_name, "UNKNOWN_ERROR")
