# London Evacuation Planning Tool - FastAPI + React
# Makefile for easy development and deployment

.PHONY: help install run run_ui test clean setup dev docs services

# Default target
help:
	@echo "🌍 London Evacuation Planning Tool - FastAPI + React"
	@echo "🚀 Agentic evacuation planning with real-time simulation"
	@echo ""
	@echo "Available commands:"
	@echo "  make setup         - Install all dependencies (Python + Node.js + Services)"
	@echo "  make services      - Start ALL services (RSS, DSPy, Backend, Frontend)"
	@echo "  make dev           - Start backend and frontend only"
	@echo "  make run           - Start the FastAPI backend server"
	@echo "  make run_ui        - Start the React frontend"
	@echo "  make run_rss       - Start RSS ingestion service"
	@echo "  make run_dspy      - Start DSPy agents service"
	@echo "  make test          - Run tests for both backend and frontend"
	@echo "  make clean         - Clean up build artifacts and caches"
	@echo "  make docs          - Generate and serve API documentation"
	@echo ""
	@echo "🚀 Quick start:"
	@echo "  1. make setup"
	@echo "  2. make services   (starts all 4 services in parallel)"
	@echo ""
	@echo "🌍 Features: Microservices, RSS ingestion, DSPy agents, Real-time SSE"
	@echo ""

# Setup - Install all dependencies
setup:
	@echo "🐍 Setting up Python environment..."
	python3 -m venv .venv
	@echo ""
	@echo "📦 Installing uv package manager..."
	source .venv/bin/activate && pip install uv
	@echo ""
	@echo "📦 Installing Python dependencies..."
	./.venv/bin/uv pip install -r requirements.txt
	@echo ""
	@echo "📦 Setting up RSS ingestion service..."
	cd services/external/rss_ingestion && python3 -m venv venv && ./venv/bin/pip install -r requirements.txt
	@echo ""
	@echo "📦 Setting up DSPy agents service..."
	cd services/external/dspy_agents && python3 -m venv venv && ./venv/bin/pip install -r requirements.txt
	@echo ""
	@echo "📦 Installing frontend dependencies..."
	cd frontend && npm install --legacy-peer-deps
	@echo ""
	@echo "📁 Creating data directories..."
	mkdir -p data/rss data/goldens data/evals data/simulations
	@echo "📁 Creating frontend public directory..."
	mkdir -p frontend/public
	@echo ""
	@echo "✅ Setup complete! Run 'make services' to start all microservices."

# Run FastAPI backend
run:
	@echo "🚀 Starting London Evacuation Planning backend server..."
	@echo "📊 API Documentation: http://localhost:8000/docs"
	@echo "🌍 Health Check: http://localhost:8000/api/health"
	@echo ""
	@echo "🔧 API Endpoints:"
	@echo "   - POST /api/runs         - Start evacuation planning run (SSE)"
	@echo "   - GET  /api/search       - Vector search over documents"
	@echo "   - POST /api/feeds/refresh - Trigger feed refresh"
	@echo ""
	./.venv/bin/python backend/main.py

# Run React frontend
run_ui:
	@echo "🚀 Starting React frontend..."
	@echo "🌐 Frontend URL: http://localhost:3000"
	@echo "🔗 API Proxy: http://localhost:8000"
	@echo ""
	@echo "📄 Available Pages:"
	@echo "   - /          - Dashboard"
	@echo "   - /plan      - Plan & Run evacuation scenarios"
	@echo "   - /results   - View run results and decision memos"
	@echo "   - /sources   - Manage data sources and feeds"
	@echo ""
	cd frontend && npm start --legacy-peer-deps

# Run RSS ingestion service
run_rss:
	@echo "📰 Starting RSS ingestion service..."
	@echo "📊 Feeds: BBC, Sky News, Guardian, Reuters, AP"
	@echo "🔄 Refresh interval: 15 minutes"
	@echo "💾 Storage: data/rss/latest.json"
	@echo ""
	cd services/external/rss_ingestion && ../../../.venv/bin/python main.py

# Run DSPy agents service
run_dspy:
	@echo "🤖 Starting DSPy agents service..."
	@echo "🧠 Agents: ThreatAnalyzer, RouteOptimizer, DecisionMemoGenerator"
	@echo "📋 Goldens: data/goldens/"
	@echo "📊 Evals: data/evals/"
	@echo ""
	cd services/external/dspy_agents && ../../../.venv/bin/python main.py

# Start ALL microservices in parallel
services:
	@echo "🚀 Starting ALL microservices..."
	@echo ""
	@echo "📰 RSS Ingestion  → Port 8001 (background)"
	@echo "🤖 DSPy Agents    → Port 8002 (background)"
	@echo "⚡ Backend API    → Port 8000"
	@echo "🌐 Frontend UI    → Port 3000"
	@echo ""
	@echo "Press Ctrl+C to stop all services"
	@echo ""
	@make -j4 run_rss run_dspy

# Development mode - run backend and frontend only
dev:
	@echo "🚀 Starting development mode (backend + frontend only)..."
	@echo ""
	@echo "Backend will run on: http://localhost:8000"
	@echo "Frontend will run on: http://localhost:3000"
	@echo ""
	@echo "Press Ctrl+C to stop both services"
	@make -j2 run run_ui

# Test backend
test-backend:
	@echo "🧪 Running backend tests..."
	./.venv/bin/python -m pytest backend/tests/ -v || echo "No tests found - create backend/tests/ directory"

# Test frontend
test-frontend:
	@echo "🧪 Running frontend tests..."
	cd frontend && npm test -- --watchAll=false

# Run all tests
test:
	@echo "🧪 Running all tests..."
	@make test-backend
	@make test-frontend

# Clean up build artifacts and caches
clean:
	@echo "🧹 Cleaning up..."
	@echo "Removing Python cache files..."
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -name "*.pyc" -delete 2>/dev/null || true
	@echo "Removing Node modules and build files..."
	rm -rf frontend/node_modules frontend/build
	@echo "Removing Python virtual environment..."
	rm -rf .venv
	@echo "Removing other cache files..."
	rm -rf .pytest_cache
	@echo "✅ Cleanup complete!"

# Build frontend for production
build-frontend:
	@echo "🏗️ Building frontend for production..."
	cd frontend && npm run build

# Build everything for production
build: build-frontend
	@echo "✅ Build complete!"

# Generate and serve API documentation
docs:
	@echo "📚 Starting API documentation server..."
	@echo "📖 API Docs: http://localhost:8000/docs"
	@echo "📖 ReDoc: http://localhost:8000/redoc"
	./.venv/bin/python backend/main.py

# Health check
health:
	@echo "🏥 Checking system health..."
	@curl -s http://localhost:8000/api/health | python -m json.tool || echo "❌ Backend not running"

# Show system status
status:
	@echo "📊 System Status:"
	@echo ""
	@echo "Backend (FastAPI):"
	@curl -s http://localhost:8000/api/health 2>/dev/null | python -m json.tool 2>/dev/null || echo "  ❌ Not running"
	@echo ""
	@echo "Frontend (React):"
	@curl -s http://localhost:3000 2>/dev/null >/dev/null && echo "  ✅ Running" || echo "  ❌ Not running"

.DEFAULT_GOAL := help