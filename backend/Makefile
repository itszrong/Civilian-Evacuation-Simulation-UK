# London Evacuation Planning Tool - FastAPI + React
.PHONY: help setup run run_ui dev test clean

help:
	@echo "🌍 London Evacuation Planning Tool"
	@echo "Available commands:"
	@echo "  make setup  - Install dependencies"
	@echo "  make run    - Start backend"
	@echo "  make run_ui - Start frontend"
	@echo "  make dev    - Start both"

setup:
	@echo "🐍 Setting up environment..."
	python3 -m venv .venv
	source .venv/bin/activate && pip install uv
	./.venv/bin/uv pip install -r requirements.txt
	cd frontend && npm install

run:
	@echo "🚀 Starting backend..."
	source .venv/bin/activate && cd backend && python main.py

run_ui:
	@echo "🚀 Starting frontend..."
	cd frontend && npm start

dev:
	@echo "🚀 Starting both services..."
	@make -j2 run run_ui

clean:
	@echo "🧹 Cleaning up..."
	rm -rf .venv frontend/node_modules

.DEFAULT_GOAL := help
