# Rate Limits

SciTeX implements rate limiting to ensure fair usage and service stability.

## Rate Limit Tiers

| Access Type | Requests/Minute | Description |
|-------------|-----------------|-------------|
| Anonymous | 10 | No API key |
| Campaign | 50 | Shared promotional key |
| User | 100 | Personal API key |

## How Rate Limiting Works

- Each request counts against your quota
- Quotas reset every 60 seconds
- Limits are per IP address (anonymous) or per API key (authenticated)

## Response Headers

Every response includes rate limit headers:

| Header | Description |
|--------|-------------|
| `X-RateLimit-Limit` | Maximum requests allowed per window |
| `X-RateLimit-Remaining` | Requests remaining in current window |
| `X-RateLimit-Window` | Window duration in seconds |
| `X-RateLimit-KeyType` | Your access type |

### Example Response Headers

```
HTTP/1.1 200 OK
X-RateLimit-Limit: 100
X-RateLimit-Remaining: 95
X-RateLimit-Window: 60
X-RateLimit-KeyType: user
```

## Handling Rate Limits

When you exceed your rate limit, you'll receive a 429 response:

```json
{
  "error": "Rate limit exceeded",
  "limit": 10,
  "window": "60 seconds",
  "key_type": "anonymous",
  "hint": "Register for an API key for higher limits"
}
```

### Best Practices

1. **Check remaining quota** before making requests
2. **Implement exponential backoff** when rate limited
3. **Cache results** when possible
4. **Use an API key** for higher limits

### Example: Handling Rate Limits in Python

```python
import requests
import time

def search_with_retry(query, max_retries=3):
    url = "{{ api_base_url }}/api/v1/scholar/search/"

    for attempt in range(max_retries):
        response = requests.get(url, params={"q": query})

        if response.status_code == 200:
            return response.json()

        if response.status_code == 429:
            # Rate limited - wait and retry
            wait_time = 2 ** attempt  # Exponential backoff
            print(f"Rate limited. Waiting {wait_time}s...")
            time.sleep(wait_time)
            continue

        response.raise_for_status()

    raise Exception("Max retries exceeded")
```

## Getting Higher Limits

Register for a free API key at [{{ api_base_url }}/accounts/api-keys/]({{ api_base_url }}/accounts/api-keys/) to increase your rate limit from 10 to 100 requests per minute.
