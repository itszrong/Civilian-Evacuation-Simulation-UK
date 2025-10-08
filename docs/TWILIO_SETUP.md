# Twilio WhatsApp Integration Setup

## ✅ Your Configuration

Your Twilio credentials are already configured in `.env`:

```
TWILIO_ACCOUNT_SID=
TWILIO_AUTH_TOKEN=
TWILIO_WHATSAPP_NUMBER= (Twilio Sandbox)
GOVERNMENT_CONTACT_NUMBER=
```

## 🚀 Quick Test

### Option 1: Test Script (Standalone)
```bash
python test_twilio.py
```

This will:
- ✅ Verify Twilio credentials
- ✅ Send test WhatsApp message to +44{phone number}
- ✅ Test notification service integration

### Option 2: Via API (Full System)
```bash
# Terminal 1 - Start backend
cd backend
uvicorn main:app --reload

# Terminal 2 - Test connection
curl -X POST http://localhost:8000/api/notifications/test-connection

# Send government alert
curl -X POST http://localhost:8000/api/notifications/government-alert \
  -H "Content-Type: application/json" \
  -d '{
    "message": "Test alert from UK Evacuation Planning System",
    "priority": "high"
  }'
```

## 📱 WhatsApp Sandbox Setup

Since you're using Twilio's sandbox number (`+14155238886`), you need to:

1. **Join the Sandbox**:
   - Open WhatsApp on your phone
   - Send a message to: `+1 415 523 8886`
   - Message content: `join <your-sandbox-code>`
   - You'll get a confirmation message

2. **Find Your Sandbox Code**:
   - Go to: https://console.twilio.com/us1/develop/sms/try-it-out/whatsapp-learn
   - Copy your unique join code
   - It looks like: `join [word-word]`

3. **Verify Connection**:
   - Once joined, run `python test_twilio.py`
   - You should receive a test message on WhatsApp

## 🎯 Example Notifications

### 1. Emergency Alert
```python
import requests

requests.post('http://localhost:8000/api/notifications/government-alert', json={
    "message": "Emergency: Westminster area evacuation ordered. Follow designated routes.",
    "priority": "critical"
})
```

### 2. Evacuation Alert (Formatted)
```python
requests.post('http://localhost:8000/api/notifications/evacuation-alert', json={
    "recipients": ["+44{phone number}"],
    "area": "Westminster",
    "route_id": "A1 - Waterloo Exit",
    "exit_points": "Waterloo Bridge, Westminster Bridge",
    "closed_roads": "Parliament Street, Whitehall, Victoria Embankment"
})
```

### 3. Simulation Complete
```python
requests.post('http://localhost:8000/api/notifications/simulation-complete', json={
    "recipients": ["+44{phone number}"],
    "run_id": "r_20250101_120000",
    "best_scenario": "Westminster Cordon Protocol",
    "clearance_time": 84.5,
    "confidence": 0.87
})
```

## 📋 Message Templates

Your system has 7 pre-configured templates:

1. **evacuation_alert** - Emergency evacuation orders
2. **evacuation_update** - Status updates during evacuation
3. **area_closure** - Area closure notifications
4. **transport_update** - Transport service changes
5. **simulation_complete** - Simulation results ready
6. **decision_memo_ready** - Decision memo for review
7. **evacuation_complete** - Evacuation completion confirmation

## 🔍 Testing Checklist

- [ ] WhatsApp sandbox joined
- [ ] Test script runs successfully: `python test_twilio.py`
- [ ] Backend starts: `cd backend && uvicorn main:app --reload`
- [ ] Test connection endpoint works
- [ ] Receive test WhatsApp message
- [ ] Government alert sends successfully
- [ ] Evacuation alert formats correctly

## 🎬 Demo Scenarios for No 10

### Scenario 1: Emergency Alert
```bash
curl -X POST http://localhost:8000/api/notifications/government-alert \
  -H "Content-Type: application/json" \
  -d '{
    "message": "DEMO: Westminster evacuation simulation complete. Best scenario achieves 84 min clearance time with 0.87 confidence.",
    "priority": "high"
  }'
```

### Scenario 2: Full Workflow
1. Run Manchester simulation (via UI)
2. System automatically sends WhatsApp notification
3. Show notification received on phone
4. Display results in web interface

### Scenario 3: Multi-City Alert
```python
# Send to multiple recipients
import requests

requests.post('http://localhost:8000/api/notifications/send-bulk', json={
    "notifications": [
        {
            "recipient": "+44{phone number}",
            "message_type": "whatsapp",
            "priority": "high",
            "custom_message": "London simulation complete. View results: http://localhost:3000/results"
        },
        {
            "recipient": "+44{phone number}",
            "message_type": "sms",
            "priority": "high",
            "custom_message": "Birmingham simulation complete. 92% success rate."
        }
    ]
})
```

## 🐛 Troubleshooting

### "Twilio Error 21211: Invalid 'To' Number"
- Make sure the recipient has joined your WhatsApp sandbox
- Verify number format: `+44{phone number}` (E.164 format)

### "Error 20003: Authentication Error"
- Check `TWILIO_AUTH_TOKEN` in `.env`
- Verify token matches Twilio Console

### "Error 21408: Permission to send SMS has not been enabled"
- Your Twilio account may need verification
- Use WhatsApp instead (more reliable for sandbox)

### Messages Not Received
1. Check WhatsApp sandbox status
2. Verify you've joined the sandbox
3. Check Twilio Console logs: https://console.twilio.com/us1/monitor/logs/messages
4. Try sending to a different number

## 🔗 Useful Links

- **Twilio Console**: https://console.twilio.com/
- **WhatsApp Sandbox**: https://console.twilio.com/us1/develop/sms/try-it-out/whatsapp-learn
- **Message Logs**: https://console.twilio.com/us1/monitor/logs/messages
- **API Docs**: http://localhost:8000/docs (when backend is running)

## 📞 Your Twilio Setup

```
Account SID: 
WhatsApp Sandbox: +1 415 523 8886
Target Number: +44 {phone number}
```

## ✨ Production Notes

For production use (not sandbox):

1. **Get Approved WhatsApp Number**:
   - Apply for WhatsApp Business API
   - Can take 1-2 weeks for approval
   - Costs ~$0.005 per message

2. **Buy Twilio Phone Number**:
   - For SMS functionality
   - UK numbers available
   - ~£1-5/month + usage

3. **Security**:
   - Add API authentication
   - Rate limiting on endpoints
   - Audit logging for compliance
   - Restrict to government IPs

---

**Status**: ✅ Ready 
