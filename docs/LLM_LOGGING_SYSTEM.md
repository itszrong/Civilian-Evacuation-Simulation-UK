# LLM Logging System Documentation

## Overview

The LLM Logging System provides comprehensive tracking and analysis of all AI/LLM API calls made by the evacuation planning system. This is critical for:

- **Audit & Compliance**: Track all AI decisions for accountability
- **Cost Management**: Monitor API usage and expenses
- **Debugging**: Review exact prompts and responses to troubleshoot issues
- **Performance Analysis**: Measure response times and token usage
- **Security**: Detect unusual patterns or potential misuse
- **Quality Improvement**: Analyze logs to refine prompts and improve system performance

## Architecture

### Components

1. **LLMLogger Class** (`backend/services/llm_service.py`)
   - Handles log file creation and writing
   - Stores logs in JSONL format (one JSON object per line)
   - Creates daily log files: `llm_calls_YYYYMMDD.jsonl`
   - Default location: `local_s3/llm_logs/`

2. **LLMService Enhancement** (`backend/services/llm_service.py`)
   - Modified `generate_text()` method to log all calls
   - Captures timing, token usage, errors
   - Supports metadata for additional context

3. **API Endpoints** (`backend/api/llm_logs.py`)
   - RESTful API for accessing and analyzing logs
   - Supports filtering, searching, and aggregation

## Log Format

Each log entry is stored as a JSON object with the following structure:

```json
{
  "call_id": "uuid-string",
  "timestamp": "2025-01-07T20:05:00.123456+00:00",
  "model": "openai/gpt-4o-mini",
  "prompt": "Full prompt text...",
  "response": "Full response text...",
  "duration_ms": 1234.56,
  "tokens_used": 350,
  "error": null,
  "metadata": {
    "user_id": "emergency_planner",
    "task_type": "scenario_generation",
    "custom_field": "value"
  }
}
```

### Field Descriptions

| Field | Type | Description |
|-------|------|-------------|
| `call_id` | string | Unique identifier for this API call (UUID) |
| `timestamp` | string | ISO 8601 timestamp (UTC) |
| `model` | string | Model identifier (e.g., "openai/gpt-4o-mini") |
| `prompt` | string | Complete prompt sent to LLM |
| `response` | string | Complete response from LLM |
| `duration_ms` | float | Time taken for API call in milliseconds |
| `tokens_used` | int | Total tokens consumed (if available) |
| `error` | string/null | Error message if call failed, null otherwise |
| `metadata` | object | Custom metadata (user_id, task_type, etc.) |

## API Endpoints

### 1. Get Logs

**Endpoint:** `GET /api/llm/logs`

**Parameters:**
- `date` (optional): Date in YYYYMMDD format (defaults to today)

**Response:**
```json
{
  "date": "20250107",
  "total_calls": 42,
  "logs": [...]
}
```

**Example:**
```bash
curl http://localhost:8000/api/llm/logs?date=20250107
```

### 2. Get Statistics

**Endpoint:** `GET /api/llm/stats`

**Parameters:**
- `date` (optional): Date in YYYYMMDD format (defaults to today)

**Response:**
```json
{
  "date": "today",
  "stats": {
    "total_calls": 42,
    "total_duration_ms": 52340.5,
    "avg_duration_ms": 1246.2,
    "total_tokens": 14500,
    "avg_tokens": 345.2,
    "errors": 2,
    "success_rate": 95.2
  }
}
```

**Example:**
```bash
curl http://localhost:8000/api/llm/stats
```

### 3. Search Logs

**Endpoint:** `GET /api/llm/logs/search`

**Parameters:**
- `date` (optional): Date in YYYYMMDD format
- `model` (optional): Filter by model name
- `min_duration` (optional): Minimum duration in ms
- `has_error` (optional): true/false to filter by error status

**Response:**
```json
{
  "date": "today",
  "filters": {
    "model": "openai/gpt-4o-mini",
    "min_duration": 1000,
    "has_error": false
  },
  "total_results": 15,
  "logs": [...]
}
```

**Examples:**
```bash
# Find slow calls (>2 seconds)
curl "http://localhost:8000/api/llm/logs/search?min_duration=2000"

# Find errors
curl "http://localhost:8000/api/llm/logs/search?has_error=true"

# Find specific model calls
curl "http://localhost:8000/api/llm/logs/search?model=openai/gpt-4o-mini"
```

### 4. Get Specific Log Entry

**Endpoint:** `GET /api/llm/logs/{call_id}`

**Parameters:**
- `call_id`: UUID of the specific log entry

**Response:**
Single log entry object

**Example:**
```bash
curl http://localhost:8000/api/llm/logs/123e4567-e89b-12d3-a456-426614174000
```

## Usage Examples

### In Code (Adding Metadata)

When calling the LLM service, you can include metadata to provide context:

```python
from services.llm_service import get_llm_service

llm_service = get_llm_service()

response = await llm_service.generate_text(
    prompt="Generate evacuation plan for Westminster",
    max_tokens=1000,
    metadata={
        "user_id": "planner_123",
        "task_type": "evacuation_planning",
        "borough": "Westminster",
        "priority": "high"
    }
)
```

### Analyzing Logs with Python

```python
import json
from pathlib import Path

# Read today's logs
log_file = Path("local_s3/llm_logs/llm_calls_20250107.jsonl")

logs = []
with open(log_file, 'r') as f:
    for line in f:
        logs.append(json.loads(line))

# Find expensive calls (>500 tokens)
expensive = [log for log in logs if log.get('tokens_used', 0) > 500]

# Calculate total cost (example pricing)
COST_PER_1K_TOKENS = 0.0001  # $0.0001 per 1K tokens
total_tokens = sum(log.get('tokens_used', 0) for log in logs)
estimated_cost = (total_tokens / 1000) * COST_PER_1K_TOKENS

print(f"Total API calls: {len(logs)}")
print(f"Total tokens: {total_tokens}")
print(f"Estimated cost: ${estimated_cost:.4f}")
```

### Command Line Analysis

```bash
# View today's logs
cat local_s3/llm_logs/llm_calls_$(date +%Y%m%d).jsonl | jq .

# Count total calls
wc -l local_s3/llm_logs/llm_calls_*.jsonl

# Find errors
cat local_s3/llm_logs/llm_calls_*.jsonl | jq 'select(.error != null)'

# Calculate average duration
cat local_s3/llm_logs/llm_calls_$(date +%Y%m%d).jsonl | \
  jq -s 'map(.duration_ms) | add / length'

# Find calls by metadata
cat local_s3/llm_logs/llm_calls_*.jsonl | \
  jq 'select(.metadata.task_type == "scenario_generation")'
```

## Storage & Retention

### File Organization

```
local_s3/
└── llm_logs/
    ├── llm_calls_20250107.jsonl
    ├── llm_calls_20250108.jsonl
    ├── llm_calls_20250109.jsonl
    └── ...
```

### Retention Policy Recommendations

1. **Keep logs for 90 days** for operational analysis
2. **Archive older logs** to cold storage if compliance requires longer retention
3. **Implement log rotation** to prevent disk space issues
4. **Consider GDPR compliance** - anonymize or delete personal data after retention period

### Disk Space Estimation

Average log size per call: ~2-5 KB
- 100 calls/day = ~500 KB/day
- 1000 calls/day = ~5 MB/day
- 10000 calls/day = ~50 MB/day

At 1000 calls/day for 90 days = ~450 MB

## Privacy & Security

### Sensitive Data Handling

⚠️ **Important**: LLM logs may contain sensitive information in prompts and responses.

**Best Practices:**
1. Store logs in secure location (not publicly accessible)
2. Implement access controls (file permissions)
3. Consider encryption at rest for sensitive deployments
4. Review logs before sharing for debugging
5. Implement data retention policies
6. Anonymize or redact sensitive data in long-term archives

### Compliance Considerations

- **GDPR**: Logs may contain personal data - ensure proper retention/deletion
- **SOC 2**: Audit trails required for security certification
- **ISO 27001**: Information security management requirements
- **Industry-specific**: Healthcare (HIPAA), Financial (PCI-DSS), etc.

## Monitoring & Alerts

### Key Metrics to Monitor

1. **Error Rate**: Percentage of failed API calls
2. **Latency**: p50, p95, p99 response times
3. **Token Usage**: Daily/hourly consumption trends
4. **Cost**: Estimated API spend
5. **Volume**: Calls per hour/day patterns

### Alert Thresholds (Examples)

- Error rate > 5%
- Average latency > 3 seconds
- Single call > 10 seconds
- Daily token usage > 100K
- No calls for 1 hour (potential system issue)

## Troubleshooting

### Log File Not Created

**Issue**: No log file in `local_s3/llm_logs/`

**Solutions:**
1. Check directory permissions
2. Verify `local_s3/` directory exists
3. Check disk space
4. Review service logs for errors

### High Token Usage

**Issue**: Unexpectedly high token consumption

**Solutions:**
1. Review prompts for unnecessary verbosity
2. Check for repeated/duplicate calls
3. Optimize prompt engineering
4. Implement caching for common queries

### Slow API Calls

**Issue**: High latency (duration_ms)

**Solutions:**
1. Check network connectivity
2. Review prompt complexity
3. Consider shorter max_tokens
4. Monitor API provider status

## Future Enhancements

Potential improvements to the logging system:

1. **Database Storage**: Move from JSONL to database for better querying
2. **Real-time Dashboards**: Grafana/Kibana integration
3. **Cost Tracking**: Integrate with billing APIs
4. **Prompt Templates**: Track performance by template
5. **A/B Testing**: Compare prompt variations
6. **Anomaly Detection**: ML-based unusual pattern detection
7. **Automated Reports**: Daily/weekly summary emails
8. **Log Compression**: Gzip older files to save space

## Related Documentation

- [LLM Service API](./API_DOCUMENTATION.md#llm-service)
- [Emergency Planning System](./EMERGENCY_PLANNING_SETUP.md)
- [System Architecture](./SYSTEM_ARCHITECTURE.md)

## Support

For questions or issues with the LLM logging system:
1. Check logs in `local_s3/llm_logs/`
2. Review structured logs in console output
3. Test API endpoints with example queries
4. Contact system administrators for access issues
