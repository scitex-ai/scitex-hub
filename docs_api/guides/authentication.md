# Authentication

The SciTeX API supports both anonymous access and authenticated access with API keys.

## Anonymous Access

No authentication required for basic usage:

```bash
curl "{{ api_base_url }}/api/v1/scholar/search/?q=neural+networks"
```

**Limits**: 10 requests per minute

## API Key Authentication

Get higher rate limits (100 requests/minute) by using an API key.

### Obtaining an API Key

1. Create an account at [{{ api_base_url }}/auth/signup/]({{ api_base_url }}/auth/signup/)
2. Navigate to [{{ api_base_url }}/accounts/api-keys/]({{ api_base_url }}/accounts/api-keys/)
3. Click "Create New API Key"
4. Copy your key (shown only once)

### Using Your API Key

#### Option 1: HTTP Header (Recommended)

```bash
curl -H "X-SCITEX-API-KEY: your-api-key-here" \
  "{{ api_base_url }}/api/v1/scholar/search/?q=neural+networks"
```

#### Option 2: Query Parameter

```bash
curl "{{ api_base_url }}/api/v1/scholar/search/?q=neural+networks&api_key=your-api-key-here"
```

!!! warning "Security Note"
    Using the query parameter exposes your API key in URLs and logs. Use the header method when possible.

## Rate Limit Headers

Every response includes rate limit information:

```
X-RateLimit-Limit: 100
X-RateLimit-Remaining: 99
X-RateLimit-Window: 60
X-RateLimit-KeyType: user
```

## Key Types

| Type | Limit | Description |
|------|-------|-------------|
| `anonymous` | 10/min | No API key provided |
| `campaign` | 50/min | Shared promotional key |
| `user` | 100/min | Personal API key |

## Error Responses

### Invalid API Key

```json
{
  "error": "Invalid API key"
}
```
HTTP Status: 401

### Rate Limit Exceeded

```json
{
  "error": "Rate limit exceeded",
  "limit": 10,
  "window": "60 seconds",
  "key_type": "anonymous",
  "hint": "Register for an API key for higher limits"
}
```
HTTP Status: 429
