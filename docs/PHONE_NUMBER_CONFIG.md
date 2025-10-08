# Phone Number Configuration

## ✅ Changes Made

All hardcoded phone numbers (`+44{phone number}`) have been removed from the codebase and replaced with environment variable references.

## 🔧 Configuration

The government contact number is now configured in **one place only**: the `.env` file

```env
GOVERNMENT_CONTACT_NUMBER=+44{phone number}
```

## 📁 Files Updated

### Backend Code Files
1. **`backend/api/notifications.py`**
   - Removed hardcoded numbers from API endpoint defaults
   - Now uses `os.getenv("GOVERNMENT_CONTACT_NUMBER")`

2. **`backend/services/notification_service.py`**
   - Updated convenience functions to read from environment
   - Removed hardcoded fallback values

3. **`backend/mcp_server.py`**
   - Updated MCP tool definitions
   - All recipient defaults now use environment variable

4. **`mcp_config.json`**
   - Changed from hardcoded value to `${GOVERNMENT_CONTACT_NUMBER}`
   - Will be replaced from environment when MCP server starts

## 🎯 How It Works Now

### Setting the Phone Number
Edit `.env` file:
```env
GOVERNMENT_CONTACT_NUMBER=+44YOURNUMBERHERE
```

### Using in Code
All notification functions automatically use this number:

```python
# In notification service
government_contact = os.getenv("GOVERNMENT_CONTACT_NUMBER")

# In API endpoints
recipients = [os.getenv("GOVERNMENT_CONTACT_NUMBER", "+44XXXXXXXXXX")]

# In MCP server
recipients = args.get("recipients", [os.getenv("GOVERNMENT_CONTACT_NUMBER")])
```

## 📋 What Still Contains the Number

### Documentation Files (Reference Only)
These files still mention `+44{phone number}` as **examples** in documentation:
- `README_GOVUK.md`
- `SETUP.md`
- `TWILIO_SETUP.md`
- `QUICK_START.md`
- `.env.template`

These are documentation files and show the format - they don't execute any code.

### Test Files
- `test_twilio.py` - Reads from `.env` file, doesn't hardcode

## ✅ Verification

Run this command to verify no hardcoded numbers in code:
```bash
grep -r "+44{phone number}" backend/ mcp_config.json --include="*.py" --include="*.json"
```

Expected result: **0 occurrences** ✅

## 🔄 Changing the Phone Number

### Option 1: Edit .env file directly
```bash
nano .env
# Change GOVERNMENT_CONTACT_NUMBER=+44{phone number}
# to your new number
```

### Option 2: Set environment variable
```bash
export GOVERNMENT_CONTACT_NUMBER="+44YOURNEWNUM"
```

### Option 3: Pass at runtime
```bash
GOVERNMENT_CONTACT_NUMBER="+44YOURNEWNUM" uvicorn main:app
```

## 🚀 Starting the System

The system will automatically pick up the phone number from `.env`:

```bash
# Backend
cd backend
uvicorn main:app --reload

# MCP Server
python backend/mcp_server.py

# Test
python test_twilio.py
```

All will use the number from `GOVERNMENT_CONTACT_NUMBER` in `.env`

## 🧪 Testing with Different Numbers

To test with a different number temporarily:
```bash
# Test script
GOVERNMENT_CONTACT_NUMBER="+44TEST123456" python test_twilio.py

# Backend
GOVERNMENT_CONTACT_NUMBER="+44TEST123456" uvicorn main:app --reload
```

## ⚠️ Important Notes

1. **E.164 Format Required**: Always use format `+44XXXXXXXXXX`
2. **No Spaces**: Don't add spaces in the phone number
3. **Include Country Code**: Always start with `+`
4. **Reload Required**: Restart backend after changing `.env`

## ✨ Benefits

- ✅ **Single Source of Truth**: One place to change the number
- ✅ **Environment Specific**: Different numbers for dev/staging/prod
- ✅ **Secure**: No hardcoded credentials in code
- ✅ **Flexible**: Easy to change without code modifications
- ✅ **MCP Compatible**: Works with AI assistants

---

**Status**: ✅ All hardcoded phone numbers removed
**Configuration**: `.env` file only
**Verified**: Zero occurrences in code files
