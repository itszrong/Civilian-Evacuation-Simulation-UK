# Quick Setup Guide for No 10 Presentation

## ⚡ 5-Minute Setup

### 1. Install Dependencies
```bash
# Install Python dependencies
pip install -r requirements.txt

# Install frontend dependencies
cd frontend
npm install
cd ..
```

### 2. Configure Twilio (Optional but Recommended)
Create `.env` file in root directory:
```env
TWILIO_ACCOUNT_SID=your_twilio_sid_here
TWILIO_AUTH_TOKEN=your_twilio_token_here
TWILIO_SMS_NUMBER=+442070000000
TWILIO_WHATSAPP_NUMBER=+442070000000
GOVERNMENT_CONTACT_NUMBER=+44{phone number}
```

**Don't have Twilio?** System works without it - notifications will just log to console.

### 3. Start the System
```bash
# Terminal 1 - Backend
cd backend
python -m uvicorn main:app --reload --host 0.0.0.0 --port 8000

# Terminal 2 - Frontend
cd frontend
npm start
```

### 4. Access the Application
- **Frontend**: http://localhost:3000
- **API Docs**: http://localhost:8000/docs
- **Health Check**: http://localhost:8000/api/health

## 🎯 Demo Flow for No 10

### Step 1: Dashboard Overview (30 seconds)
1. Navigate to http://localhost:3000
2. Show GOV.UK compliant design
3. Highlight multi-city support

### Step 2: Run London Simulation (2 minutes)
1. Click "Plan & Run" in navigation
2. Select "London" as city
3. Set objective: "minimise clearance time and improve fairness"
4. Click "Run Planning Session"
5. Watch real-time SSE updates
6. Show real evacuation routes on map

### Step 3: Compare Multiple Scenarios (1 minute)
1. Navigate to "Results"
2. Show scenario rankings with real metrics
3. Display decision memo with evidence
4. Demonstrate interactive visualisations

### Step 4: Test Other UK Cities (1 minute)
1. Go to "Sources" or "Dashboard"
2. Select different cities: Manchester, Birmingham, Edinburgh
3. Show instant simulation capability
4. Demonstrate Scotland/Wales/England coverage

### Step 5: NYC Visualisation (30 seconds)
1. Navigate to Results
2. Select "Manhattan" from city selector
3. Show grid-based heatmap
4. Explain biased random walk algorithm

### Step 6: Emergency Notifications (1 minute)
1. Open API docs: http://localhost:8000/docs
2. Navigate to "notifications" section
3. Try "POST /api/notifications/government-alert"
4. Send test message to +44{phone number}
5. Check WhatsApp for delivery

### Step 7: MCP Integration Demo (Optional, 2 minutes)
1. Start MCP server: `python backend/mcp_server.py`
2. Connect with Claude Desktop
3. Ask: "Run an evacuation simulation for Bristol"
4. Show AI executing tools automatically

## 🔍 Key Features to Demonstrate

### ✅ Real Simulations
- No mock data - all results from actual graph algorithms
- Real OpenStreetMap street networks
- A* pathfinding for evacuation routes

### ✅ Multi-City Support
- **25+ UK Cities**: London, Birmingham, Manchester, Glasgow, Edinburgh, Leeds, Liverpool, etc.
- **Automatic Network Loading**: Just select a city, system handles the rest
- **Scotland, Wales, Northern Ireland**: Full UK coverage

### ✅ Emergency Communications
- WhatsApp integration for rapid alerts
- SMS backup for connectivity issues
- Pre-formatted templates for consistency
- Bulk notification support

### ✅ AI Integration
- Full MCP server implementation
- AI assistants can control the entire system
- Automatic scenario comparison
- Intelligent decision support

### ✅ Government Standards
- GOV.UK Design System compliance
- WCAG 2.1 AA accessibility
- Audit logging for accountability
- Export functionality for records

## 🐛 Troubleshooting

### Backend Won't Start
```bash
# Check Python version (need 3.10+)
python --version

# Install missing dependencies
pip install fastapi uvicorn structlog

# Try running directly
cd backend
python main.py
```

### Frontend Won't Start
```bash
# Clear cache
rm -rf node_modules package-lock.json
npm install

# Check Node version (need 16+)
node --version
```

### Notifications Not Working
1. **Check Twilio credentials** in `.env`
2. **Verify phone number format**: Must be E.164 (+44{phone number})
3. **Check Twilio console** for account status
4. **Test without Twilio**: System logs notifications to console

### Simulation Errors
1. **OSMnx issues**: Make sure `osmnx`, `networkx`, `geopandas` are installed
2. **City not found**: Try different city name or use coordinates
3. **Slow loading**: First load downloads street network (cached afterwards)

## 📊 System Requirements

### Minimum
- Python 3.10+
- Node.js 16+
- 4GB RAM
- 2GB disk space

### Recommended (for demos)
- Python 3.11+
- Node.js 18+
- 8GB RAM
- 5GB disk space (for multiple city caches)
- SSD storage

## 🔐 Security for Production

### Before deploying to production:
1. **Enable authentication**: Add API key middleware
2. **Configure HTTPS**: Use reverse proxy (nginx)
3. **Restrict origins**: Update CORS settings
4. **Rate limiting**: Protect endpoints
5. **Environment secrets**: Use proper secret management
6. **Logging**: Configure structured logging to secure location
7. **Backup**: Regular database and artifact backups

## 📞 Support Contacts

- **Technical Support**: [Your contact]
- **Emergency Hotline**: [Your number]
- **Documentation**: See README_GOVUK.md

## ✨ Quick API Tests

### Test Health
```bash
curl http://localhost:8000/api/health
```

### Test Cities List
```bash
curl http://localhost:8000/api/simulation/cities
```

### Test Manchester Simulation
```bash
curl -X POST http://localhost:8000/api/simulation/manchester/run \
  -H "Content-Type: application/json" \
  -d '{"num_simulations": 5, "num_routes": 3}'
```

### Test Notification
```bash
curl -X POST http://localhost:8000/api/notifications/government-alert \
  -H "Content-Type: application/json" \
  -d '{"message": "Test from No 10 demo", "priority": "low"}'
```

## 🎥 Screen Recording Tips

1. **Use high resolution**: 1920x1080 minimum
2. **Clear browser cache**: Fresh start
3. **Close other tabs**: Focus on demo
4. **Prepare test data**: Have scenarios ready
5. **Test network**: Stable connection for OSM downloads

## ⚡ Performance Tips

### For Faster Demos
1. **Pre-cache cities**: Run simulations beforehand
2. **Use SSD**: Faster graph loading
3. **Increase workers**: More parallel processing
4. **Local network**: Avoid public WiFi

### For Better Visualisations
1. **Use Chrome**: Best rendering
2. **Full screen**: Hide browser UI
3. **Zoom 100%**: Standard scaling
4. **Dark mode off**: Better projector visibility

---

**Ready for No 10 Downing Street & National Situation Centre** 🇬🇧
