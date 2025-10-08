"""
London Evacuation Planning Tool - Main FastAPI Application

This is the main entry point for the London-focused evacuation planning tool
that provides agentic workflows for emergency planning scenarios.
"""

import logging
import os
import sys
from contextlib import asynccontextmanager
from typing import Dict, Any

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import structlog

from core.config import get_settings
from api.health import router as health_router
from api.feeds import router as feeds_router
from api.search import router as search_router
from api.runs import router as runs_router
from api.artifacts import router as artifacts_router
from api.simulation import router as simulation_router
from api.notifications import router as notifications_router
from api.rss import router as rss_router
from api.emergency_chat import router as emergency_chat_router
from api.metrics import router as metrics_router
from api.agentic import router as agentic_router
from api.simulation_queue import router as simulation_queue_router
from api.civil_unrest import router as civil_unrest_router
from api.framework_scenarios import router as framework_scenarios_router
from api.evaluation import router as evaluation_router
from api.chat import router as chat_router
from api.llm_logs import router as llm_logs_router


# Get settings early to configure logging appropriately
settings = get_settings()

# Configure structured logging based on environment
if settings.DEBUG:
    # Development: Use human-readable console output with more detail
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        stream=sys.stdout
    )
    
    structlog.configure(
        processors=[
            structlog.stdlib.filter_by_level,
            structlog.stdlib.add_logger_name,
            structlog.stdlib.add_log_level,
            structlog.stdlib.PositionalArgumentsFormatter(),
            structlog.processors.TimeStamper(fmt="%Y-%m-%d %H:%M:%S"),
            structlog.dev.ConsoleRenderer(colors=True)  # Colorized console output
        ],
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )
    
    # Set log levels for various components
    logging.getLogger("uvicorn.access").setLevel(logging.INFO)
    logging.getLogger("uvicorn.error").setLevel(logging.INFO)
    logging.getLogger("fastapi").setLevel(logging.INFO)
    
else:
    # Production: Use JSON output for structured logging
    logging.basicConfig(level=logging.WARNING)
    
    structlog.configure(
        processors=[
            structlog.stdlib.filter_by_level,
            structlog.stdlib.add_logger_name,
            structlog.stdlib.add_log_level,
            structlog.stdlib.PositionalArgumentsFormatter(),
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.JSONRenderer()
        ],
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )

logger = structlog.get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager for startup and shutdown events."""
    # Startup
    print("🚀 Starting London Evacuation Planning Tool API")
    logger.info("Starting London Evacuation Planning Tool API", 
                debug_mode=settings.DEBUG,
                host=settings.HOST,
                port=settings.PORT)
    
    # Log configuration details in debug mode
    if settings.DEBUG:
        logger.info("Configuration loaded",
                   allowed_origins=settings.allowed_origins_list,
                   local_storage=settings.LOCAL_STORAGE_PATH,
                   ai_services_configured=bool(settings.OPENAI_API_KEY or settings.ANTHROPIC_API_KEY))
    
    # Initialize core services here if needed
    # await initialize_graph_service()
    # await initialize_data_feeds()
    
    yield
    
    # Shutdown
    print("🛑 Shutting down London Evacuation Planning Tool API")
    logger.info("Shutting down London Evacuation Planning Tool API")


def create_application() -> FastAPI:
    """Create and configure the FastAPI application."""
    
    app = FastAPI(
        title="London Evacuation Planning Tool",
        description="Agentic evacuation planning system with real-time simulation and RAG-based decision support",
        version="1.0.0",
        docs_url="/docs" if settings.DEBUG else None,
        redoc_url="/redoc" if settings.DEBUG else None,
        lifespan=lifespan
    )
    
    # Configure CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.allowed_origins_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    # Include routers with logging
    logger.info("Registering API routes")
    app.include_router(health_router, prefix="/api", tags=["health"])
    app.include_router(feeds_router, prefix="/api", tags=["feeds"])
    app.include_router(search_router, prefix="/api", tags=["search"])
    app.include_router(runs_router, prefix="/api", tags=["runs"])
    app.include_router(artifacts_router, prefix="/api", tags=["artifacts"])
    app.include_router(simulation_router, prefix="/api/simulation", tags=["simulation"])
    app.include_router(notifications_router, prefix="/api/notifications", tags=["notifications"])
    app.include_router(rss_router, tags=["rss"])
    app.include_router(emergency_chat_router, prefix="/api/emergency", tags=["emergency"])
    app.include_router(metrics_router, prefix="/api", tags=["metrics"])
    app.include_router(agentic_router, prefix="/api", tags=["agentic"])
    app.include_router(simulation_queue_router, tags=["simulation-queue"])
    app.include_router(civil_unrest_router, tags=["civil-unrest"])
    app.include_router(framework_scenarios_router, tags=["framework-scenarios"])
    app.include_router(evaluation_router, prefix="/api", tags=["evaluation"])
    app.include_router(chat_router, tags=["chat"])
    app.include_router(llm_logs_router, prefix="/api/llm", tags=["llm-logs"])
    
    @app.exception_handler(Exception)
    async def global_exception_handler(request, exc):
        """Global exception handler with structured logging."""
        logger.error(
            "Unhandled exception",
            exc_info=exc,
            path=request.url.path,
            method=request.method,
            client_ip=request.client.host if request.client else "unknown"
        )
        return JSONResponse(
            status_code=500,
            content={
                "error": "Internal server error",
                "detail": str(exc) if settings.DEBUG else "An unexpected error occurred"
            }
        )
    
    @app.get("/")
    async def root():
        """Root endpoint."""
        logger.info("Root endpoint accessed")
        return {
            "service": "London Evacuation Planning Tool",
            "version": "1.0.0",
            "status": "operational",
            "features": [
                "agentic_planning",
                "real_time_simulation", 
                "rag_based_explanations",
                "sovereign_storage",
                "streaming_results"
            ]
        }
    
    return app


# Create the application instance
app = create_application()


if __name__ == "__main__":
    import uvicorn
    
    print(f"🌍 Starting server on {settings.HOST}:{settings.PORT}")
    print(f"🔧 Debug mode: {settings.DEBUG}")
    print(f"📊 API docs: http://localhost:{settings.PORT}/docs")
    
    uvicorn.run(
        "main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG,
        log_level="info" if settings.DEBUG else "warning",
        access_log=True
    )
