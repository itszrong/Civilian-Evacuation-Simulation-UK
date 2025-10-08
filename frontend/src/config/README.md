# API Configuration

This directory contains the centralized API configuration for the Intelligence Analysis frontend.

## Files

- `api.js` - Main API configuration with endpoints and utilities

## Environment Configuration

The API configuration supports multiple environments:

- **local** - `http://localhost:8000` (default)
- **dev** - `https://dev-api.intelligence.gov`
- **staging** - `https://staging-api.intelligence.gov`
- **production** - `https://api.intelligence.gov`

## Environment Variables

Create a `.env.local` file in the frontend root directory with these variables:

```bash
# API Environment (local, dev, staging, production)
REACT_APP_API_ENV=local

# Override specific API URL (optional)
REACT_APP_API_URL=http://localhost:8000

# Feature flags
REACT_APP_ENABLE_DEBUG_API=true
REACT_APP_ENABLE_MOCK_DATA=false

# Authentication settings
REACT_APP_AUTH_TIMEOUT=30000
REACT_APP_TOKEN_REFRESH_THRESHOLD=300000
```

## API Endpoints

All API endpoints are centralized in `API_ENDPOINTS`:

### Authentication
- `auth.login` - `/auth/login`
- `auth.refresh` - `/auth/refresh`
- `auth.me` - `/auth/me`
- `auth.logout` - `/auth/logout`

### Intelligence/Reports
- `intelligence.ingest` - `/intelligence/ingest`
- `intelligence.getById(id)` - `/intelligence/{id}`
- `intelligence.list` - `/intelligence`
- `intelligence.dashboard` - `/reports/dashboard`

### Agent Management
- `agents.types` - `/agents/types`
- `agents.create` - `/agents/create`
- `agents.list` - `/agents`
- `agents.getById(id)` - `/agents/{id}`
- `agents.updateConfig(id)` - `/agents/{id}/config`
- `agents.remove(id)` - `/agents/{id}`
- `agents.systemHealth` - `/agents/system/health`
- `agents.createPool` - `/agents/pool/create`

### System
- `system.health` - `/system/health`
- `system.status` - `/system/status`
- `system.metrics` - `/system/metrics`

## Usage Examples

### Basic API Call
```javascript
import { apiRequest, API_ENDPOINTS, REQUEST_CONFIG } from '../config/api.js';

// GET request
const data = await apiRequest(
  API_ENDPOINTS.system.health,
  REQUEST_CONFIG.get()
);

// POST request with authentication
const result = await apiRequest(
  API_ENDPOINTS.intelligence.ingest,
  REQUEST_CONFIG.post(reportData, token)
);
```

### Using Utility Functions
```javascript
import { buildUrl, buildUrlWithParams, getAuthHeaders } from '../config/api.js';

// Build URL
const url = buildUrl('/api/custom-endpoint');

// Build URL with query parameters
const urlWithParams = buildUrlWithParams('/api/search', {
  query: 'threat',
  limit: 10
});

// Get auth headers
const headers = getAuthHeaders(userToken);
```

### Error Handling
```javascript
import { apiRequest, handleApiError } from '../config/api.js';

try {
  const data = await apiRequest(endpoint, config);
  // Handle success
} catch (error) {
  // Error is already processed by handleApiError
  console.error('API Error:', error.message);
}
```

## Debugging

Enable debug mode by setting `REACT_APP_ENABLE_DEBUG_API=true`. This will:
- Log API configuration on startup
- Provide additional error details
- Show request/response information in console

Use the `debugApi()` function to inspect current configuration:

```javascript
import { debugApi } from '../config/api.js';

debugApi(); // Logs current API configuration
```

## Migration from Direct Fetch

To migrate existing fetch calls:

### Before
```javascript
const response = await fetch(`http://localhost:8000/auth/login`, {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json',
  },
  body: JSON.stringify(loginData),
});

if (!response.ok) {
  throw new Error('Login failed');
}

return response.json();
```

### After
```javascript
import { apiRequest, API_ENDPOINTS, REQUEST_CONFIG } from '../config/api.js';

return apiRequest(
  API_ENDPOINTS.auth.login,
  REQUEST_CONFIG.post(loginData)
);
```

This provides:
- Environment switching
- Automatic error handling
- Retry logic
- Consistent headers
- Type safety (when using TypeScript)
