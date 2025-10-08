# 🚀 Quick Start - UK Evacuation Planning System

## ⚡ 3-Step Setup

### 1. Install Dependencies
```bash
# Install Python packages
pip install -r requirements.txt

# Install Node packages
cd frontend && npm install && cd ..
```

### 2. Test Twilio (Optional)
```bash
# Make sure you've joined the WhatsApp sandbox first!
python test_twilio.py
```

### 3. Start System
```bash
# Terminal 1 - Backend
cd backend
uvicorn main:app --reload --host 0.0.0.0 --port 8000

# Terminal 2 - Frontend
cd frontend
npm start
```

## 🎯 Access Points

- **Frontend**: http://localhost:3000
- **API Docs**: http://localhost:8000/docs
- **Health**: http://localhost:8000/api/health

## 📱 Quick Tests

### Test WhatsApp
```bash
python test_twilio.py
```

### Test API
```bash
curl http://localhost:8000/api/health
curl http://localhost:8000/api/simulation/cities
```

### Send Alert
```bash
curl -X POST http://localhost:8000/api/notifications/government-alert \
  -H "Content-Type: application/json" \
  -d '{"message": "Test alert", "priority": "high"}'
```

## 🏙️ Run Simulations

### Via UI
1. Go to http://localhost:3000
2. Click "Plan & Run"
3. Select city (London, Manchester, Birmingham, etc.)
4. Click "Run Planning Session"

### Via API
```bash
# London
curl -X POST http://localhost:8000/api/simulation/london/run \
  -H "Content-Type: application/json" \
  -d '{"num_routes": 8}'

# Manchester
curl -X POST http://localhost:8000/api/simulation/manchester/run \
  -H "Content-Type: application/json" \
  -d '{"num_routes": 5}'

# Birmingham
curl -X POST http://localhost:8000/api/simulation/birmingham/run \
  -H "Content-Type: application/json" \
  -d '{"num_routes": 5}'
```

## 🇬🇧 Supported UK Cities

London • Birmingham • Manchester • Glasgow • Edinburgh • Leeds • Liverpool • Bristol • Sheffield • Newcastle • Cardiff • Belfast • Nottingham • Leicester • Coventry • Bradford • Southampton • Brighton • Plymouth • Cambridge • Oxford • York • Bath • Durham • Canterbury

## 📊 Features

✅ 25+ UK cities
✅ Manhattan NYC grid simulation
✅ WhatsApp & SMS notifications
✅ Real OSMnx street networks
✅ A* pathfinding
✅ MCP server for AI assistants
✅ GOV.UK design system
✅ Real-time results (no mocks)

## 🎬 No 10 Demo Flow

1. **Dashboard** → Show multi-city support
2. **Run London** → Real-time simulation
3. **View Results** → Decision memo with evidence
4. **Test Birmingham** → Instant capability
5. **Send Alert** → WhatsApp notification
6. **Show Manhattan** → NYC heatmap

## 🐛 Common Issues

**Backend won't start?**
```bash
cd backend
pip install fastapi uvicorn structlog twilio mcp
python main.py
```

**Frontend won't start?**
```bash
cd frontend
rm -rf node_modules package-lock.json
npm install
npm start
```

**WhatsApp not working?**
1. Join sandbox: Send `join [code]` to +1 415 523 8886
2. Check `.env` has correct credentials
3. Run `python test_twilio.py`

## 📞 Your Configuration

```
Twilio Account: 
WhatsApp Sandbox: +1 415 523 8886
Government Contact: +44 7376 278333
```

## 🔗 Documentation

- **Full README**: See `README_GOVUK.md`
- **Setup Guide**: See `SETUP.md`
- **Twilio Guide**: See `TWILIO_SETUP.md`

---

**Ready for No 10 Downing Street! 🇬🇧**
