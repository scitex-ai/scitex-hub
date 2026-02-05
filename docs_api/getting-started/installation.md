# Installation

The SciTeX API is a REST API that requires no installation. You can access it directly via HTTP requests.

## Requirements

- Any HTTP client (curl, wget, Postman, etc.)
- Or any programming language with HTTP support

## Quick Test

Test the API is working:

```bash
curl "{{ api_base_url }}/api/v1/scholar/info/"
```

You should receive a JSON response with API documentation.

## Client Libraries

### Python

Use the `requests` library:

```bash
pip install requests
```

```python
import requests

response = requests.get(
    "{{ api_base_url }}/api/v1/scholar/search/",
    params={"q": "neural networks"}
)
print(response.json())
```

### JavaScript/Node.js

Use fetch (browser) or node-fetch:

```javascript
const response = await fetch(
  "{{ api_base_url }}/api/v1/scholar/search/?q=neural+networks"
);
const data = await response.json();
console.log(data);
```

### R

Use the `httr` package:

```r
library(httr)
library(jsonlite)

response <- GET(
  "{{ api_base_url }}/api/v1/scholar/search/",
  query = list(q = "neural networks")
)
data <- fromJSON(content(response, "text"))
```

## Next Steps

- [Quick Start Guide](quickstart.md) - Your first API call
- [Scholar Search API](../api/scholar.md) - Full API reference
- [Authentication](../guides/authentication.md) - Get an API key
