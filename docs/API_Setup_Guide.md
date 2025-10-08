# Intelligence Analysis API Setup Guide

## 🚀 Quick Start with Appwrite

### 1. Start Appwrite Backend

```bash
cd appwrite-local/appwrite
docker compose up -d
```

Wait for Appwrite to be ready at `http://localhost`

### 2. Install Dependencies

```bash
cd backend
pip install -r requirements.txt
```

### 3. Setup Database & Users

```bash
python setup_appwrite_intelligence.py
```

This will:
- Create Appwrite database and collections
- Set up storage buckets and teams
- Create test users with different clearance levels
- Validate the complete setup

### 4. Start the API Server

```bash
cd backend
python start_server.py
```

The server will start on `http://localhost:8000`

### 5. Access API Documentation

- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc
- **Appwrite Console**: http://localhost

### 6. Test the API

```bash
python test_api.py
```

---

## 🏗️ Architecture Overview

### SOTA Repositories Integrated

✅ **ruptures** - Advanced changepoint detection for regime analysis  
✅ **uncertainty-toolbox** - Professional model calibration  
✅ **calibration-framework** - Neural network confidence calibration  
✅ **pycasbin** - Role-based access control for classification levels  

### Core Services

1. **IntelligenceService** - Intelligence ingestion and processing
2. **ProbabilisticService** - Bayesian analysis with TensorFlow Probability and PyMC
3. **RegimeDetectionService** - Time series regime change detection
4. **CalibrationService** - Model uncertainty quantification and calibration
5. **AuthService** - JWT-based authentication
6. **AccessControlService** - Classification-level access control

---

## 🔐 Authentication

### Test Users (Appwrite)

| Email | Password | Role | Clearance Level | Department |
|-------|----------|------|----------------|------------|
| `analyst1@intelligence.gov` | `password123` | ANALYST | SECRET | MI5 |
| `senior1@intelligence.gov` | `senior123` | SENIOR_ANALYST | TOP_SECRET | GCHQ |
| `supervisor1@intelligence.gov` | `super123` | SUPERVISOR | TOP_SECRET | MI6 |

### Login Example

```bash
curl -X POST "http://localhost:8000/auth/login" \
  -H "Content-Type: application/json" \
  -d '{"username": "analyst1@intelligence.gov", "password": "password123"}'
```

Or use just the username (email domain will be added automatically):

```bash
curl -X POST "http://localhost:8000/auth/login" \
  -H "Content-Type: application/json" \
  -d '{"username": "analyst1", "password": "password123"}'
```

---

## 📊 API Endpoints

### Authentication & Authorization
- `POST /auth/login` - User authentication
- `POST /auth/refresh` - Refresh JWT token
- `GET /auth/me` - Get user profile

### Intelligence Processing
- `POST /intelligence/ingest` - Ingest raw intelligence
- `GET /intelligence/{id}` - Retrieve processed intelligence
- `GET /intelligence` - List intelligence reports with filtering

### Probabilistic Analysis
- `POST /analysis/probabilistic` - Create probabilistic event analysis
- `PUT /analysis/probabilistic/{id}/update` - Update with new evidence
- `POST /analysis/monte-carlo` - Run Monte Carlo simulations

### Regime Detection
- `POST /analysis/regime-detection` - Detect regime changes in time series
- `GET /analysis/threat-evolution/{region}` - Analyze threat evolution

### Model Calibration
- `POST /calibration/assess` - Assess model calibration
- `POST /calibration/temperature-scaling` - Apply temperature scaling

### Intelligence Fusion
- `POST /fusion/multi-source` - Fuse multi-source intelligence
- `GET /fusion/source-reliability` - Get source reliability scores

### Executive Reporting
- `POST /reports/executive-summary` - Generate executive summaries
- `GET /reports/dashboard` - Get dashboard data

### Prediction Markets
- `POST /prediction-market/create` - Create prediction market
- `POST /prediction-market/{id}/predict` - Place prediction
- `GET /prediction-market` - List active markets

### System Monitoring
- `GET /system/health` - Health check
- `GET /system/metrics` - System performance metrics

---

## 🎯 Usage Examples

### 1. Ingest Intelligence

```python
import requests

# Login first
auth_response = requests.post("http://localhost:8000/auth/login", json={
    "username": "analyst1",
    "password": "password123"
})
token = auth_response.json()["access_token"]

headers = {"Authorization": f"Bearer {token}"}

# Ingest intelligence
intel_data = {
    "content": "SIGINT intercepts show increased military communications in Eastern Europe.",
    "source": "GCHQ_SIGINT",
    "classification_level": "SECRET",
    "estimated_priority": "SUBSTANTIAL",
    "notes": "Requires cross-referencing with satellite imagery"
}

response = requests.post(
    "http://localhost:8000/intelligence/ingest",
    json=intel_data,
    headers=headers
)

result = response.json()
print(f"Intelligence ID: {result['intelligence_id']}")
print(f"Confidence: {result['confidence_score']:.2f}")
```

### 2. Create Probabilistic Analysis

```python
analysis_data = {
    "event_description": "Military escalation in Eastern Europe",
    "event_type": "MILITARY_ACTION",
    "initial_probability": 0.4,
    "time_horizon_days": 30
}

response = requests.post(
    "http://localhost:8000/analysis/probabilistic",
    json=analysis_data,
    headers=headers
)

analysis = response.json()
print(f"Event probability: {analysis['event']['probability']:.2%}")
print(f"Credible interval: {analysis['event']['credible_interval']}")
```

### 3. Update with Evidence

```python
evidence_data = {
    "evidence": [
        {
            "evidence_id": "EV001",
            "description": "Satellite imagery confirms military buildup", 
            "evidence_type": "SUPPORTS",
            "strength": 8.0,
            "reliability": 0.9,
            "classification_level": "SECRET",
            "source": "NRO_IMAGERY"
        }
    ]
}

response = requests.put(
    f"http://localhost:8000/analysis/probabilistic/{analysis_id}/update",
    json=evidence_data,
    headers=headers
)

updated = response.json()
print(f"Updated probability: {updated['event']['probability']:.2%}")
print(f"Evidence impact: {updated['bayesian_update']['evidence_impact']:.2%}")
```

### 4. Detect Regime Changes

```python
# Generate time series data
time_series_data = [
    {"timestamp": "2024-01-01T00:00:00", "value": 0.3},
    {"timestamp": "2024-01-01T06:00:00", "value": 0.35},
    # ... more data points
]

regime_data = {
    "time_series_data": time_series_data,
    "detection_method": "pelt",
    "minimum_segment_length": 5
}

response = requests.post(
    "http://localhost:8000/analysis/regime-detection",
    json=regime_data,
    headers=headers
)

regimes = response.json()
print(f"Changepoints detected: {len(regimes['changepoints'])}")
print(f"Current regime: {regimes['current_regime']['regime_type']}")
```

---

## 🔧 Advanced Features

### WebSocket Support

Real-time intelligence updates via WebSocket:

```javascript
const ws = new WebSocket('ws://localhost:8000/ws/user123');

ws.onmessage = function(event) {
    const update = JSON.parse(event.data);
    console.log('Intelligence update:', update);
};
```

### Classification Level Security

The system enforces proper classification levels:

- **UNCLASSIFIED** → Access to public information only
- **RESTRICTED** → Access to UNCLASSIFIED + internal use
- **SECRET** → Access to RESTRICTED + sensitive intelligence  
- **TOP SECRET** → Access to all classification levels

### Need-to-Know Filtering

Access is also filtered by:
- Department (MI5, MI6, GCHQ, etc.)
- Role (Analyst, Senior Analyst, Supervisor)
- Source compatibility

---

## 🧪 Testing

### Automated Test Suite

Run the comprehensive test suite:

```bash
python test_api.py
```

Tests cover:
- ✅ Authentication & authorization
- ✅ Intelligence ingestion & retrieval
- ✅ Probabilistic analysis & Bayesian updating
- ✅ Regime detection with SOTA algorithms
- ✅ Monte Carlo simulations
- ✅ Model calibration & uncertainty quantification
- ✅ Dashboard data & executive summaries

### Manual Testing

Use the interactive API documentation at `http://localhost:8000/docs` to test individual endpoints.

---

## 🚨 Security Features

### JWT Authentication
- Secure token-based authentication
- Configurable token expiration
- Role and clearance level embedded in tokens

### Access Control
- Casbin-based RBAC (Role-Based Access Control)
- Classification level hierarchy enforcement
- Need-to-know principle implementation
- Audit logging for all access attempts

### Data Protection
- Automatic content redaction based on clearance levels
- Source attribution filtering
- Secure session management

---

## 📈 Monitoring & Metrics

### Health Checks
```bash
curl http://localhost:8000/system/health
```

### Performance Metrics
```bash
curl -H "Authorization: Bearer $TOKEN" \
  http://localhost:8000/system/metrics
```

### Real-time Dashboards
Access filtered dashboards based on your clearance level:
```bash
curl -H "Authorization: Bearer $TOKEN" \
  http://localhost:8000/reports/dashboard
```

---

## 🔄 Integration with Frontend

The API is designed to work with modern frontend frameworks:

```javascript
// Example React integration
const useIntelligenceAPI = () => {
    const [token, setToken] = useState(null);
    
    const login = async (username, password) => {
        const response = await fetch('/auth/login', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ username, password })
        });
        
        const data = await response.json();
        setToken(data.access_token);
        return data;
    };
    
    const ingestIntelligence = async (intelData) => {
        return fetch('/intelligence/ingest', {
            method: 'POST',
            headers: {
                'Authorization': `Bearer ${token}`,
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(intelData)
        });
    };
    
    return { login, ingestIntelligence };
};
```

---

## 🎓 Next Steps

1. **Scale the System**: Add Redis for caching, PostgreSQL for persistence
2. **Enhanced Security**: Implement OAuth2, multi-factor authentication
3. **Real-time Processing**: Add Kafka for event streaming
4. **Advanced Analytics**: Integrate more SOTA ML models
5. **Visualisation**: Create interactive threat analysis dashboards
6. **Deployment**: Containerize with Docker, deploy to Kubernetes

---

## 📚 Documentation

- **API Reference**: http://localhost:8000/docs
- **SOTA Integration Guide**: `integration_examples.md`
- **Repository Recommendations**: `SOTA_repositories_recommendations.md`
- **Probabilistic Framework**: `probabilistic_intelligence_framework.md`
- **Uncertainty Extraction**: `transformer_uncertainty_extraction.md`

---

## 🆘 Troubleshooting

### Common Issues

**Import Errors**: Install dependencies with `pip install -r requirements.txt`

**Permission Denied**: Check user clearance level matches required classification

**Token Expired**: Use `/auth/refresh` endpoint to get new token

**Port Already in Use**: Change port in `start_server.py` or kill existing process

### Logs

Check server logs for detailed error information:
```bash
tail -f /tmp/intelligence_api.log
```

---

Your intelligence analysis API is now ready with SOTA probabilistic reasoning, uncertainty quantification, and professional-grade security! 🎉
