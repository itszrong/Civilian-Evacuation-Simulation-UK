"""
Unit tests for ErrorHandler service.
Tests unified error handling, logging, and user feedback.
"""

import pytest
import tempfile
import shutil
import json
from pathlib import Path
from unittest.mock import Mock, patch
from datetime import datetime

from services.error_handler import (
    ErrorHandler, StandardError, ErrorSeverity, ErrorCategory, ErrorContext,
    get_error_handler, handle_simulation_errors, handle_graph_errors, handle_api_errors
)


class TestErrorSeverity:
    """Test ErrorSeverity enum."""
    
    def test_severity_values(self):
        """Test severity enum values."""
        assert ErrorSeverity.LOW.value == "low"
        assert ErrorSeverity.MEDIUM.value == "medium"
        assert ErrorSeverity.HIGH.value == "high"
        assert ErrorSeverity.CRITICAL.value == "critical"


class TestErrorCategory:
    """Test ErrorCategory enum."""
    
    def test_category_values(self):
        """Test category enum values."""
        assert ErrorCategory.VALIDATION.value == "validation"
        assert ErrorCategory.NETWORK.value == "network"
        assert ErrorCategory.SIMULATION.value == "simulation"
        assert ErrorCategory.GRAPH_LOADING.value == "graph_loading"
        assert ErrorCategory.SYSTEM.value == "system"
        assert ErrorCategory.UNKNOWN.value == "unknown"


class TestErrorContext:
    """Test ErrorContext dataclass."""
    
    def test_error_context_creation(self):
        """Test error context creation."""
        context = ErrorContext(
            error_id="test-123",
            timestamp="2024-01-01T00:00:00",
            service_name="test_service",
            operation_name="test_operation",
            user_id="user123",
            request_id="req456",
            additional_data={"key": "value"}
        )
        
        assert context.error_id == "test-123"
        assert context.timestamp == "2024-01-01T00:00:00"
        assert context.service_name == "test_service"
        assert context.operation_name == "test_operation"
        assert context.user_id == "user123"
        assert context.request_id == "req456"
        assert context.additional_data == {"key": "value"}


class TestStandardError:
    """Test StandardError dataclass."""
    
    @pytest.fixture
    def sample_context(self):
        """Create sample error context."""
        return ErrorContext(
            error_id="test-123",
            timestamp="2024-01-01T00:00:00",
            service_name="test_service",
            operation_name="test_operation"
        )
    
    def test_standard_error_creation(self, sample_context):
        """Test standard error creation."""
        error = StandardError(
            error_id="test-123",
            error_code="TEST_ERROR",
            message="Test error message",
            user_message="User-friendly message",
            severity=ErrorSeverity.HIGH,
            category=ErrorCategory.VALIDATION,
            context=sample_context,
            technical_details="Stack trace here",
            suggested_actions=["Action 1", "Action 2"],
            retry_after=30
        )
        
        assert error.error_id == "test-123"
        assert error.error_code == "TEST_ERROR"
        assert error.message == "Test error message"
        assert error.user_message == "User-friendly message"
        assert error.severity == ErrorSeverity.HIGH
        assert error.category == ErrorCategory.VALIDATION
        assert error.technical_details == "Stack trace here"
        assert error.suggested_actions == ["Action 1", "Action 2"]
        assert error.retry_after == 30
    
    def test_to_dict(self, sample_context):
        """Test converting error to dictionary."""
        error = StandardError(
            error_id="test-123",
            error_code="TEST_ERROR",
            message="Test message",
            user_message="User message",
            severity=ErrorSeverity.MEDIUM,
            category=ErrorCategory.NETWORK,
            context=sample_context,
            suggested_actions=["Try again"],
            retry_after=60
        )
        
        error_dict = error.to_dict()
        
        assert error_dict["error_id"] == "test-123"
        assert error_dict["error_code"] == "TEST_ERROR"
        assert error_dict["message"] == "Test message"
        assert error_dict["user_message"] == "User message"
        assert error_dict["severity"] == "medium"
        assert error_dict["category"] == "network"
        assert error_dict["suggested_actions"] == ["Try again"]
        assert error_dict["retry_after"] == 60
    
    def test_to_user_dict(self, sample_context):
        """Test converting error to user-friendly dictionary."""
        error = StandardError(
            error_id="test-123",
            error_code="TEST_ERROR",
            message="Technical message",
            user_message="User-friendly message",
            severity=ErrorSeverity.LOW,
            category=ErrorCategory.VALIDATION,
            context=sample_context,
            technical_details="Secret technical details",
            suggested_actions=["Check input"]
        )
        
        user_dict = error.to_user_dict()
        
        assert user_dict["error_id"] == "test-123"
        assert user_dict["message"] == "User-friendly message"
        assert user_dict["severity"] == "low"
        assert user_dict["suggested_actions"] == ["Check input"]
        
        # Technical details should not be included
        assert "technical_details" not in user_dict
        assert "error_code" not in user_dict


class TestErrorHandler:
    """Test ErrorHandler class."""
    
    @pytest.fixture
    def temp_log_dir(self):
        """Create temporary log directory."""
        temp_dir = tempfile.mkdtemp()
        yield temp_dir
        shutil.rmtree(temp_dir)
    
    @pytest.fixture
    def error_handler(self, temp_log_dir):
        """Create ErrorHandler for testing."""
        return ErrorHandler("test_service", log_dir=temp_log_dir)
    
    def test_error_handler_initialization(self, error_handler, temp_log_dir):
        """Test error handler initialization."""
        assert error_handler.service_name == "test_service"
        assert error_handler.log_dir == Path(temp_log_dir)
        assert error_handler.log_dir.exists()
        assert len(error_handler.error_history) == 0
        assert len(error_handler.error_counts) == 0
    
    def test_handle_exception_error(self, error_handler):
        """Test handling an exception."""
        try:
            raise ValueError("Test exception")
        except Exception as e:
            standard_error = error_handler.handle_error(
                error=e,
                error_code="INVALID_INPUT",
                operation_name="test_operation",
                user_id="user123"
            )
        
        assert isinstance(standard_error, StandardError)
        assert standard_error.error_code == "INVALID_INPUT"
        assert standard_error.message == "Test exception"
        assert standard_error.severity == ErrorSeverity.MEDIUM
        assert standard_error.category == ErrorCategory.VALIDATION
        assert standard_error.context.service_name == "test_service"
        assert standard_error.context.operation_name == "test_operation"
        assert standard_error.context.user_id == "user123"
        assert standard_error.technical_details is not None
    
    def test_handle_string_error(self, error_handler):
        """Test handling a string error."""
        standard_error = error_handler.handle_error(
            error="String error message",
            error_code="SYSTEM_ERROR",
            operation_name="test_op"
        )
        
        assert isinstance(standard_error, StandardError)
        assert standard_error.message == "String error message"
        assert standard_error.technical_details is None
    
    def test_handle_error_without_code(self, error_handler):
        """Test handling error without explicit error code."""
        try:
            raise KeyError("Missing key")
        except Exception as e:
            standard_error = error_handler.handle_error(
                error=e,
                operation_name="test_operation"
            )
        
        assert standard_error.error_code == "MISSING_REQUIRED_FIELD"  # Inferred from KeyError
    
    def test_infer_error_code(self, error_handler):
        """Test error code inference from exception types."""
        test_cases = [
            (ValueError("test"), "INVALID_INPUT"),
            (KeyError("test"), "MISSING_REQUIRED_FIELD"),
            (TimeoutError("test"), "NETWORK_TIMEOUT"),
            (ConnectionError("test"), "CONNECTION_FAILED"),
            (FileNotFoundError("test"), "INSUFFICIENT_DATA"),
            (MemoryError("test"), "RESOURCE_EXHAUSTED"),
            (RuntimeError("test"), "UNKNOWN_ERROR")
        ]
        
        for exception, expected_code in test_cases:
            inferred_code = error_handler._infer_error_code(exception)
            assert inferred_code == expected_code
    
    def test_error_tracking(self, error_handler):
        """Test error tracking and statistics."""
        # Handle multiple errors
        error_handler.handle_error("Error 1", "INVALID_INPUT", "op1")
        error_handler.handle_error("Error 2", "INVALID_INPUT", "op2")
        error_handler.handle_error("Error 3", "NETWORK_TIMEOUT", "op3")
        
        assert len(error_handler.error_history) == 3
        
        # Check error counts
        validation_key = "validation:INVALID_INPUT"
        network_key = "network:NETWORK_TIMEOUT"
        
        assert validation_key in error_handler.error_counts
        assert network_key in error_handler.error_counts
        assert error_handler.error_counts[validation_key]["count"] == 2
        assert error_handler.error_counts[network_key]["count"] == 1
    
    def test_get_error_statistics(self, error_handler):
        """Test error statistics generation."""
        # Handle some errors
        error_handler.handle_error("Error 1", "INVALID_INPUT", "op1")
        error_handler.handle_error("Error 2", "NETWORK_TIMEOUT", "op2")
        
        stats = error_handler.get_error_statistics()
        
        assert "summary" in stats
        assert "by_severity" in stats
        assert "by_category" in stats
        assert "error_counts" in stats
        assert "recent_errors" in stats
        
        assert stats["summary"]["total_errors"] == 2
        assert stats["summary"]["service"] == "test_service"
        assert "medium" in stats["by_severity"]
        assert "high" in stats["by_severity"]
        assert "validation" in stats["by_category"]
        assert "network" in stats["by_category"]
    
    def test_get_error_statistics_empty(self, error_handler):
        """Test error statistics with no errors."""
        stats = error_handler.get_error_statistics()
        
        assert stats == {"message": "No errors recorded"}
    
    def test_create_api_response(self, error_handler):
        """Test API response creation."""
        standard_error = error_handler.handle_error(
            "Test error",
            "TEST_ERROR",
            "test_operation"
        )
        
        # User response (no technical details)
        user_response = error_handler.create_api_response(standard_error, include_technical=False)
        
        assert "error_id" in user_response
        assert "message" in user_response
        assert "service" in user_response
        assert "operation" in user_response
        assert "technical_details" not in user_response
        
        # Technical response (with technical details)
        tech_response = error_handler.create_api_response(standard_error, include_technical=True)
        
        assert "error_code" in tech_response
        assert "technical_details" in tech_response or tech_response.get("technical_details") is None
    
    def test_custom_user_message(self, error_handler):
        """Test custom user message override."""
        custom_message = "Custom user-friendly message"
        
        standard_error = error_handler.handle_error(
            "Technical error",
            "INVALID_INPUT",
            "test_op",
            custom_user_message=custom_message
        )
        
        assert standard_error.user_message == custom_message
    
    def test_error_with_additional_data(self, error_handler):
        """Test error handling with additional context data."""
        additional_data = {
            "input_value": "invalid_data",
            "expected_format": "json"
        }
        
        standard_error = error_handler.handle_error(
            "Invalid input format",
            "INVALID_INPUT",
            "parse_input",
            additional_data=additional_data
        )
        
        assert standard_error.context.additional_data == additional_data
    
    @patch('services.error_handler.logger')
    def test_logging_levels(self, mock_logger, error_handler):
        """Test that different severity levels use appropriate logging."""
        # Critical error
        error_handler.handle_error("Critical error", "SYSTEM_OVERLOAD", "test_op")
        mock_logger.critical.assert_called()
        
        # High severity error
        error_handler.handle_error("High error", "SIMULATION_FAILED", "test_op")
        mock_logger.error.assert_called()
        
        # Medium severity error
        error_handler.handle_error("Medium error", "INVALID_INPUT", "test_op")
        mock_logger.warning.assert_called()
    
    def test_error_log_file_creation(self, error_handler, temp_log_dir):
        """Test that error log files are created for high severity errors."""
        # Handle a high severity error
        error_handler.handle_error("Critical system error", "SYSTEM_OVERLOAD", "test_op")
        
        # Check that log file was created
        log_files = list(Path(temp_log_dir).glob("errors_*.json"))
        assert len(log_files) > 0
        
        # Check log file content
        with open(log_files[0], 'r') as f:
            log_entry = json.loads(f.readline())
        
        assert "error_id" in log_entry
        assert "service" in log_entry
        assert log_entry["service"] == "test_service"
        assert "Critical system error" in log_entry["message"]


class TestErrorHandlerDecorators:
    """Test error handler decorators."""
    
    def test_handle_simulation_errors_decorator(self):
        """Test simulation error decorator."""
        @handle_simulation_errors("test_simulation")
        def failing_simulation():
            raise ValueError("Simulation failed")
        
        result = failing_simulation()
        
        assert "error" in result
        assert "error_id" in result["error"]
        assert "message" in result["error"]
    
    def test_handle_graph_errors_decorator(self):
        """Test graph error decorator."""
        @handle_graph_errors("load_graph")
        def failing_graph_load():
            raise ConnectionError("Cannot load graph")
        
        result = failing_graph_load()
        
        assert "error" in result
        assert "error_id" in result["error"]
    
    def test_handle_api_errors_decorator(self):
        """Test API error decorator."""
        @handle_api_errors("api_endpoint")
        def failing_api_call():
            raise RuntimeError("API error")
        
        result = failing_api_call()
        
        assert "error" in result
        assert "error_id" in result["error"]
    
    @pytest.mark.asyncio
    async def test_async_decorator(self):
        """Test decorator with async function."""
        @handle_simulation_errors("async_simulation")
        async def failing_async_simulation():
            raise ValueError("Async simulation failed")
        
        result = await failing_async_simulation()
        
        assert "error" in result
        assert "error_id" in result["error"]
    
    def test_decorator_success_case(self):
        """Test decorator when function succeeds."""
        @handle_simulation_errors("successful_simulation")
        def successful_simulation():
            return {"status": "success", "data": "result"}
        
        result = successful_simulation()
        
        assert "error" not in result
        assert result["status"] == "success"
        assert result["data"] == "result"


class TestGlobalErrorHandlers:
    """Test global error handler management."""
    
    def test_get_error_handler_singleton(self):
        """Test that get_error_handler returns singleton instances."""
        handler1 = get_error_handler("test_service")
        handler2 = get_error_handler("test_service")
        
        assert handler1 is handler2
        assert handler1.service_name == "test_service"
    
    def test_get_error_handler_different_services(self):
        """Test that different services get different handlers."""
        handler1 = get_error_handler("service1")
        handler2 = get_error_handler("service2")
        
        assert handler1 is not handler2
        assert handler1.service_name == "service1"
        assert handler2.service_name == "service2"


class TestErrorHandlerIntegration:
    """Integration tests for ErrorHandler."""
    
    @pytest.fixture
    def temp_log_dir(self):
        """Create temporary log directory."""
        temp_dir = tempfile.mkdtemp()
        yield temp_dir
        shutil.rmtree(temp_dir)
    
    def test_full_error_handling_workflow(self, temp_log_dir):
        """Test complete error handling workflow."""
        handler = ErrorHandler("integration_test", log_dir=temp_log_dir)
        
        # Simulate a real error scenario
        try:
            # Simulate a simulation that fails due to invalid input
            invalid_config = {"invalid": "config"}
            if "city" not in invalid_config:
                raise ValueError("Missing required field: city")
        except Exception as e:
            standard_error = handler.handle_error(
                error=e,
                error_code="MISSING_REQUIRED_FIELD",
                operation_name="run_simulation",
                user_id="user123",
                request_id="req456",
                additional_data={"config": invalid_config}
            )
        
        # Verify error was properly handled
        assert isinstance(standard_error, StandardError)
        assert standard_error.error_code == "MISSING_REQUIRED_FIELD"
        assert standard_error.category == ErrorCategory.VALIDATION
        assert standard_error.severity == ErrorSeverity.MEDIUM
        
        # Verify tracking
        assert len(handler.error_history) == 1
        assert "validation:MISSING_REQUIRED_FIELD" in handler.error_counts
        
        # Verify API response creation
        api_response = handler.create_api_response(standard_error)
        assert "error_id" in api_response
        assert "service" in api_response
        assert api_response["service"] == "integration_test"
        
        # Verify statistics
        stats = handler.get_error_statistics()
        assert stats["summary"]["total_errors"] == 1
        assert "validation" in stats["by_category"]
    
    def test_error_code_configurations(self):
        """Test that all predefined error codes are properly configured."""
        handler = ErrorHandler("test_service")
        
        required_fields = ["category", "severity", "user_message"]
        
        for error_code, config in handler.error_codes.items():
            # Check required fields
            for field in required_fields:
                assert field in config, f"Error code {error_code} missing {field}"
            
            # Check types
            assert isinstance(config["category"], ErrorCategory)
            assert isinstance(config["severity"], ErrorSeverity)
            assert isinstance(config["user_message"], str)
            
            # Check optional fields
            if "suggested_actions" in config:
                assert isinstance(config["suggested_actions"], list)
            if "retry_after" in config:
                assert isinstance(config["retry_after"], int)
                assert config["retry_after"] > 0
