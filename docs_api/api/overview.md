# API Overview

The SciTeX API provides RESTful endpoints for searching academic literature across multiple sources.

## Base URL

```
{{ api_base_url }}/api/v1/
```

## Available Endpoints

### Scholar API

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/scholar/search/` | Search academic papers |
| GET | `/scholar/info/` | API documentation and status |

## Response Format

All endpoints return JSON by default. The Scholar Search API also supports BibTeX, CSV, and plain text formats via the `format` parameter.

### Standard JSON Response

```json
{
  "status": "success",
  "query": "neural networks",
  "total_count": 42,
  "sources": {
    "pubmed": {"count": 15, "status": "success"},
    "arxiv": {"count": 12, "status": "success"},
    "semantic": {"count": 15, "status": "success"}
  },
  "results": [...]
}
```

### Error Response

```json
{
  "error": "Error message",
  "detail": "Additional details"
}
```

## HTTP Status Codes

| Code | Description |
|------|-------------|
| 200 | Success |
| 400 | Bad Request - Invalid parameters |
| 401 | Unauthorized - Invalid API key |
| 405 | Method Not Allowed |
| 429 | Too Many Requests - Rate limit exceeded |
| 500 | Internal Server Error |

## Rate Limiting

All endpoints are rate limited. See [Rate Limits Guide](../guides/rate-limits.md) for details.

Rate limit information is included in response headers:

- `X-RateLimit-Limit`: Maximum requests per window
- `X-RateLimit-Remaining`: Remaining requests
- `X-RateLimit-Window`: Window duration in seconds
- `X-RateLimit-KeyType`: Your access type (anonymous, campaign, user)
