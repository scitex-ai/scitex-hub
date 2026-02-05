# SciTeX API Documentation

Welcome to the SciTeX API documentation. SciTeX provides programmatic access to academic literature search across multiple sources.

## Features

- **Multi-source Search**: Query PubMed, arXiv, Semantic Scholar, CrossRef, and OpenAlex simultaneously
- **Multiple Export Formats**: JSON, BibTeX, CSV, and plain text
- **Rate Limiting**: Fair usage with higher limits for authenticated users
- **Citation Metrics**: Includes citation counts and journal impact factors

## Quick Start

Search for papers using a simple HTTP GET request:

```bash
curl "{{ api_base_url }}/api/v1/scholar/search/?q=neural+networks&limit=10"
```

Export as BibTeX:

```bash
curl "{{ api_base_url }}/api/v1/scholar/search/?q=deep+learning&format=bibtex"
```

## API Endpoints

| Endpoint | Description |
|----------|-------------|
| `{{ api_base_url }}/api/v1/scholar/search/` | Search academic literature |
| `{{ api_base_url }}/api/v1/scholar/info/` | API documentation and status |

## Rate Limits

| Access Type | Limit |
|-------------|-------|
| Anonymous | 10 requests/minute |
| With API Key | 100 requests/minute |

## Getting an API Key

Register at [{{ api_base_url }}/accounts/api-keys/]({{ api_base_url }}/accounts/api-keys/) to get higher rate limits.

## Next Steps

- [Quick Start Guide](getting-started/quickstart.md)
- [Scholar Search API Reference](api/scholar.md)
- [Authentication Guide](guides/authentication.md)
