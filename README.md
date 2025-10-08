# London Evacuation Planning System

## 🚨 AI-Powered Emergency Planning & Evacuation Simulation

A comprehensive emergency planning platform that combines real-world geographic data, advanced pathfinding algorithms, and artificial intelligence to create realistic evacuation simulations for urban areas with a focus on London.

## 🌟 Key Features

### Core Capabilities
- **Real-World Geographic Integration**: OpenStreetMap data via OSMnx for accurate street networks
- **AI-Powered Scenario Generation**: Natural language interface for creating evacuation scenarios
- **Advanced Agent-Based Simulation**: A* pathfinding with realistic behavioral modeling
- **Interactive Visualizations**: Folium and Mesa-based real-time visualization
- **Multi-Borough Support**: Comprehensive coverage of all 33 London boroughs
- **Decision Support System**: AI-generated recommendations and analysis
- **Emergency Notifications**: Twilio SMS integration for stakeholder alerts

### Technical Highlights
- **FastAPI Backend**: High-performance async API with OpenAPI documentation
- **React Frontend**: Government design system (GOV.UK) compliant interface
- **DSPy AI Agents**: Intelligent planning, scenario generation, and analysis
- **Mesa Framework**: Agent-based modeling with real-time visualization
- **OSMnx Integration**: Street network analysis and routing
- **Scalable Architecture**: Async processing with configurable concurrency

## 🚀 Quick Start

### Prerequisites
- Python 3.10+
- Node.js 16+
- npm or yarn
- uv (Python package manager) - install with: `pip install uv`

### Installation

```bash
# Clone repository
git clone <repository-url>
cd Civilian-Evacuation-Simulation-UK

# Setup all dependencies (Python + Node.js + Services)
make setup
```

### Configuration

```bash
# Copy environment template
cp .env.template .env

# Configure required environment variables
# - OpenAI API key (for AI features)
# - Twilio credentials (for notifications)
# - Other service configurations
```

### Running the Application

```bash
# Option 1: Start all services (recommended)
make services

# Option 2: Start backend and frontend only
npm run build && npm run start

# Option 3: Start individual services
make run          # Backend only
make run_ui       # Frontend only

# Access application
open http://localhost:3000
```

### Available Commands

The project includes a comprehensive Makefile with the following commands:

```bash
make setup         # Install all dependencies (Python + Node.js + Services)
make services      # Start ALL services (RSS, DSPy, Backend, Frontend)
make dev           # Start backend and frontend only
make run           # Start the FastAPI backend server
make run_ui        # Start the React frontend
make test          # Run tests for both backend and frontend
make clean         # Clean up build artifacts and caches
make help          # Show all available commands
```

## 📁 Project Structure

```
├── backend/              # FastAPI backend application
│   ├── api/             # API endpoints
│   ├── services/        # Core simulation and AI services
│   ├── agents/          # DSPy AI agents
│   ├── models/          # Data models
│   └── main.py          # Application entry point
├── frontend/            # React frontend application
│   └── src/
│       ├── components/  # React components
│       ├── services/    # API clients
│       └── config/      # Configuration
├── docs/                # Documentation
├── tests/               # Test suites
└── local_s3/           # Local storage for artifacts
```

## 📚 Documentation

Comprehensive documentation is available in the [`docs/`](docs/) directory:

### Getting Started
- **[Quick Start Guide](docs/QUICK_START.md)** - Get up and running in 10 minutes
- **[Setup Guide](docs/SETUP.md)** - Detailed installation and configuration
- **[User Guide](docs/USER_GUIDE.md)** - Complete user documentation

### Technical Documentation
- **[System Architecture](docs/SYSTEM_ARCHITECTURE.md)** - System design and patterns
- **[API Documentation](docs/API_DOCUMENTATION.md)** - Complete API reference
- **[Technical Implementation Guide](docs/TECHNICAL_IMPLEMENTATION_GUIDE.md)** - Implementation details

### Features & Configuration
- **[Agentic System Summary](docs/AGENTIC_SYSTEM_SUMMARY.md)** - AI agent capabilities
- **[Deployment Guide](docs/DEPLOYMENT_GUIDE.md)** - Production deployment
- **[Configuration Guides](docs/)** - Various setup guides (Twilio, caching, etc.)

See **[Documentation Index](docs/INDEX.md)** for complete documentation listing.

## 🏗️ Architecture Overview

### Backend Services
- **Simulation Engine**: OSMnx-based evacuation modeling
- **AI Agents**: DSPy-powered scenario generation and analysis
- **API Layer**: FastAPI with async request handling
- **Storage**: JSON-based artifact storage with caching
- **Notifications**: Twilio SMS integration

### Frontend Application
- **Framework**: React with TypeScript
- **Design System**: GOV.UK compliant components
- **Visualization**: Interactive maps and charts
- **State Management**: React hooks and context
- **API Integration**: Axios-based REST client

## 🧪 Testing

```bash
# Run all tests (backend + frontend)
make test

# Run individual test suites
make test-backend    # Backend tests only
make test-frontend   # Frontend tests only
```

## 📊 Use Cases

- **Emergency Planning**: Simulate evacuation scenarios for disaster preparedness
- **Infrastructure Assessment**: Identify bottlenecks and capacity issues
- **Policy Analysis**: Evaluate different evacuation strategies
- **Training**: Educate emergency responders on evacuation dynamics
- **Research**: Study urban evacuation patterns and behaviors

## 🔒 Security & Compliance

- Environment-based configuration management
- API key protection
- Data privacy considerations for emergency planning
- GOV.UK design standards compliance
- Secure external service integration (Twilio)

## 🤝 Contributing

For development contributions:
1. Review the [Technical Implementation Guide](docs/TECHNICAL_IMPLEMENTATION_GUIDE.md)
2. Follow existing code patterns and standards
3. Ensure tests pass before submitting changes
4. Update documentation for new features

## 📝 License

See LICENSE file for details.

## 📞 Support

For questions or issues:
- Review the [Documentation](docs/INDEX.md)
- Check the [Quick Start Guide](docs/QUICK_START.md)
- Consult the [User Guide](docs/USER_GUIDE.md)

---

**System Version**: 1.0  
**Last Updated**: October 2025
