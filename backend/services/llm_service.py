"""
Shared LLM Service

Provides a centralized service for making LLM calls using DSPy.
Can be used by emergency planning, scenario generation, and other AI features.
Includes comprehensive logging of all LLM calls for audit and analysis.
"""

import structlog
import json
import uuid
from typing import Optional, Dict, Any
from datetime import datetime, timezone
from pathlib import Path
import time
from core.config import get_settings

try:
    import dspy
    DSPY_AVAILABLE = True
except ImportError:
    DSPY_AVAILABLE = False
    dspy = None

logger = structlog.get_logger(__name__)


class LLMLogger:
    """Logger for all LLM API calls."""
    
    def __init__(self, log_dir: str = "local_s3/llm_logs"):
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(parents=True, exist_ok=True)
        self.current_log_file = self.log_dir / f"llm_calls_{datetime.now(timezone.utc).strftime('%Y%m%d')}.jsonl"
        logger.info(f"LLM Logger initialized, logging to: {self.current_log_file}")
    
    def log_call(
        self,
        call_id: str,
        model: str,
        prompt: str,
        response: str,
        duration_ms: float,
        tokens_used: Optional[int] = None,
        error: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ):
        """Log an LLM API call to local storage."""
        log_entry = {
            "call_id": call_id,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "model": model,
            "prompt": prompt,
            "response": response,
            "duration_ms": duration_ms,
            "tokens_used": tokens_used,
            "error": error,
            "metadata": metadata or {}
        }
        
        try:
            # Append to JSONL file (one JSON object per line)
            with open(self.current_log_file, 'a', encoding='utf-8') as f:
                f.write(json.dumps(log_entry, ensure_ascii=False) + '\n')
            
            # Also log to structured logger for real-time monitoring
            logger.info(
                "LLM API call completed",
                call_id=call_id,
                model=model,
                duration_ms=duration_ms,
                tokens_used=tokens_used,
                prompt_length=len(prompt),
                response_length=len(response),
                error=error
            )
        except Exception as e:
            logger.error(f"Failed to log LLM call: {e}", exc_info=True)
    
    def get_logs_for_date(self, date: str = None) -> list:
        """Retrieve logs for a specific date (YYYYMMDD format)."""
        if date is None:
            date = datetime.now(timezone.utc).strftime('%Y%m%d')
        
        log_file = self.log_dir / f"llm_calls_{date}.jsonl"
        if not log_file.exists():
            return []
        
        logs = []
        try:
            with open(log_file, 'r', encoding='utf-8') as f:
                for line in f:
                    if line.strip():
                        logs.append(json.loads(line))
        except Exception as e:
            logger.error(f"Failed to read logs: {e}")
        
        return logs
    
    def get_stats(self, date: str = None) -> Dict[str, Any]:
        """Get statistics for LLM calls on a specific date."""
        logs = self.get_logs_for_date(date)
        
        if not logs:
            return {
                "total_calls": 0,
                "total_duration_ms": 0,
                "total_tokens": 0,
                "errors": 0
            }
        
        total_duration = sum(log['duration_ms'] for log in logs)
        total_tokens = sum(log.get('tokens_used', 0) for log in logs if log.get('tokens_used'))
        errors = sum(1 for log in logs if log.get('error'))
        
        return {
            "total_calls": len(logs),
            "total_duration_ms": total_duration,
            "avg_duration_ms": total_duration / len(logs),
            "total_tokens": total_tokens,
            "avg_tokens": total_tokens / len(logs) if total_tokens else 0,
            "errors": errors,
            "success_rate": (len(logs) - errors) / len(logs) * 100 if logs else 0
        }


class LLMService:
    """Centralized service for LLM operations using DSPy with comprehensive logging."""
    
    def __init__(self):
        self.settings = get_settings()
        self.lm = None
        self.llm_logger = LLMLogger()
        self.model_name = None
        self._initialize_dspy()
    
    def _initialize_dspy(self):
        """Initialize DSPy with LLM configuration from settings."""
        if not DSPY_AVAILABLE:
            logger.warning("DSPy not available, LLM calls will be mocked")
            return
            
        try:
            # Try OpenAI first, fall back to Anthropic
            if self.settings.OPENAI_API_KEY:
                logger.info("Initializing DSPy LLM Service with OpenAI")
                self.model_name = 'openai/gpt-4o-mini'
                # DSPy 2.4+ uses unified LM interface
                self.lm = dspy.LM(
                    model=self.model_name,
                    api_key=self.settings.OPENAI_API_KEY,
                    max_tokens=2000
                )
                logger.info("Successfully initialized DSPy LLM Service with OpenAI")
            elif self.settings.ANTHROPIC_API_KEY:
                logger.info("Initializing DSPy LLM Service with Anthropic Claude")
                self.model_name = 'anthropic/claude-sonnet-4-5'
                # DSPy 2.4+ uses unified LM interface
                self.lm = dspy.LM(
                    model=self.model_name,
                    api_key=self.settings.ANTHROPIC_API_KEY,
                    max_tokens=2000
                )
                logger.info("Successfully initialized DSPy LLM Service with Anthropic Claude")
            else:
                logger.warning("No LLM API key found in settings, using mock responses")
                self.lm = None
                return

            # Configure DSPy globally
            dspy.configure(lm=self.lm)
            logger.info("DSPy LLM Service ready")

        except Exception as e:
            logger.error(f"Failed to initialize DSPy LLM Service: {e}", exc_info=True)
            self.lm = None
    
    def is_available(self) -> bool:
        """Check if LLM service is available and configured."""
        return DSPY_AVAILABLE and self.lm is not None
    
    def create_module(self, module_class):
        """Create a DSPy module instance if LLM is available."""
        if not self.is_available():
            return None
        return module_class()
    
    async def generate_text(
        self, 
        prompt: str, 
        max_tokens: int = 1000,
        metadata: Optional[Dict[str, Any]] = None,
        functions: Optional[list] = None,
        function_call: Optional[str] = None
    ) -> str:
        """
        Generate text using the configured LLM with comprehensive logging.
        Supports function calling for tool use.
        
        Args:
            prompt: Input prompt
            max_tokens: Maximum tokens to generate
            metadata: Optional metadata to include in logs (e.g., user_id, task_type)
            functions: Optional list of function definitions for function calling
            function_call: Optional function call behavior ('auto', 'none', or specific function)
            
        Returns:
            Generated text or mock response if LLM unavailable
        """
        call_id = str(uuid.uuid4())
        start_time = time.time()
        response_text = ""
        error = None
        tokens_used = None
        
        try:
            if not self.is_available():
                response_text = f"Mock response for: {prompt[:100]}..."
                error = "LLM not available (mock mode)"
                return response_text
            
            # Use DSPy's direct LM interface for text generation
            response = self.lm(prompt, max_tokens=max_tokens)
            
            # Extract response text - handle different response formats
            if hasattr(response, 'choices'):
                response_text = response.choices[0].message.content
            elif isinstance(response, list):
                # If response is a list, get the first element
                response_text = str(response[0]) if response else ""
            else:
                response_text = str(response)
            
            # Ensure we have a string, not an array
            if isinstance(response_text, list):
                response_text = response_text[0] if response_text else ""
            
            # Try to extract token usage if available
            if hasattr(response, 'usage'):
                tokens_used = response.usage.total_tokens
            
            return response_text
            
        except Exception as e:
            error = str(e)
            logger.error(f"LLM generation failed: {e}")
            response_text = f"Error generating response: {str(e)}"
            return response_text
            
        finally:
            # Log the call regardless of success/failure
            duration_ms = (time.time() - start_time) * 1000
            self.llm_logger.log_call(
                call_id=call_id,
                model=self.model_name or "unknown",
                prompt=prompt,
                response=response_text,
                duration_ms=duration_ms,
                tokens_used=tokens_used,
                error=error,
                metadata=metadata
            )
    
    
    def get_logs(self, date: str = None) -> list:
        """
        Retrieve LLM call logs for a specific date.
        
        Args:
            date: Date in YYYYMMDD format, defaults to today
            
        Returns:
            List of log entries
        """
        return self.llm_logger.get_logs_for_date(date)
    
    def get_stats(self, date: str = None) -> Dict[str, Any]:
        """
        Get statistics for LLM calls.
        
        Args:
            date: Date in YYYYMMDD format, defaults to today
            
        Returns:
            Dictionary with statistics
        """
        return self.llm_logger.get_stats(date)


# Global instance
_llm_service = None

def get_llm_service() -> LLMService:
    """Get the global LLM service instance."""
    global _llm_service
    if _llm_service is None:
        _llm_service = LLMService()
    return _llm_service
