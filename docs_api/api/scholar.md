# Scholar Search API

Search academic literature across multiple sources including PubMed, arXiv, Semantic Scholar, CrossRef, and OpenAlex.

## Endpoint

```
GET {{ api_base_url }}/api/v1/scholar/search/
```

## Parameters

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `q` | string | Yes | - | Search query |
| `limit` | integer | No | 20 | Maximum results per source (max: 100) |
| `format` | string | No | json | Response format: `json`, `bibtex`, `csv`, `text` |
| `sources` | string | No | pubmed,arxiv,semantic | Comma-separated list of sources |

### Available Sources

| Source | Description |
|--------|-------------|
| `pubmed` | PubMed/MEDLINE biomedical literature |
| `arxiv` | arXiv preprints (physics, math, CS, etc.) |
| `semantic` | Semantic Scholar academic papers |
| `crossref` | CrossRef DOI metadata |
| `openalex` | OpenAlex open scholarly metadata |

## Examples

### Basic Search

```bash
curl "{{ api_base_url }}/api/v1/scholar/search/?q=neural+networks"
```

### With Limit

```bash
curl "{{ api_base_url }}/api/v1/scholar/search/?q=machine+learning&limit=50"
```

### Specific Sources

```bash
curl "{{ api_base_url }}/api/v1/scholar/search/?q=cancer&sources=pubmed,crossref"
```

### BibTeX Export

```bash
curl "{{ api_base_url }}/api/v1/scholar/search/?q=deep+learning&format=bibtex" \
  -o references.bib
```

### CSV Export

```bash
curl "{{ api_base_url }}/api/v1/scholar/search/?q=covid&format=csv&sources=pubmed" \
  -o papers.csv
```

### With API Key (Higher Rate Limits)

```bash
curl -H "X-SCITEX-API-KEY: your-api-key" \
  "{{ api_base_url }}/api/v1/scholar/search/?q=neural+networks"
```

Or via query parameter:

```bash
curl "{{ api_base_url }}/api/v1/scholar/search/?q=neural+networks&api_key=your-key"
```

## Response Formats

### JSON (default)

```json
{
  "status": "success",
  "query": "neural networks",
  "total_count": 60,
  "sources": {
    "pubmed": {"count": 20, "status": "success"},
    "arxiv": {"count": 20, "status": "success"},
    "semantic": {"count": 20, "status": "success"}
  },
  "results": [
    {
      "title": "Deep Learning in Neural Networks: An Overview",
      "authors": "Schmidhuber, Jurgen",
      "journal": "Neural Networks",
      "year": "2015",
      "doi": "10.1016/j.neunet.2014.09.003",
      "pmid": "",
      "arxiv_id": "",
      "citations": 15000,
      "impact_factor": 7.8,
      "is_open_access": false,
      "abstract": "In recent years, deep artificial neural networks...",
      "url": "https://doi.org/10.1016/j.neunet.2014.09.003",
      "source": "semantic"
    }
  ]
}
```

### BibTeX

```bibtex
@article{schmidhuber2015deep,
  author = {Schmidhuber, Jurgen},
  title = {Deep Learning in Neural Networks: An Overview},
  journal = {Neural Networks},
  year = {2015},
  doi = {10.1016/j.neunet.2014.09.003},
  citations = {15000},
  impactfactor = {7.8},
  abstract = {In recent years, deep artificial neural networks...},
}
```

### CSV

| Title | Authors | Journal | Year | DOI | PMID | arXiv ID | Citations | Impact Factor | Open Access | Source | URL | Abstract |
|-------|---------|---------|------|-----|------|----------|-----------|---------------|-------------|--------|-----|----------|
| Deep Learning... | Schmidhuber | Neural Networks | 2015 | 10.1016/... | | | 15000 | 7.8 | No | semantic | https://... | In recent... |

### Plain Text

```
[1] Deep Learning in Neural Networks: An Overview
Authors: Schmidhuber, Jurgen
Journal: Neural Networks
Year: 2015
Citations: 15000
Impact Factor: 7.8
DOI: 10.1016/j.neunet.2014.09.003
URL: https://doi.org/10.1016/j.neunet.2014.09.003
Abstract: In recent years, deep artificial neural networks...

---

[2] ...
```

## Response Fields

| Field | Type | Description |
|-------|------|-------------|
| `title` | string | Paper title |
| `authors` | string | Author names (comma-separated) |
| `journal` | string | Journal or venue name |
| `year` | string | Publication year |
| `doi` | string | Digital Object Identifier |
| `pmid` | string | PubMed ID |
| `arxiv_id` | string | arXiv identifier |
| `citations` | integer | Citation count |
| `impact_factor` | float | Journal impact factor |
| `is_open_access` | boolean | Whether paper is open access |
| `abstract` | string | Paper abstract |
| `url` | string | Link to paper |
| `source` | string | Data source (pubmed, arxiv, etc.) |

## Error Responses

### Missing Query

```json
{
  "error": "Missing required parameter: q",
  "example": "/api/v1/scholar/search/?q=neural+networks",
  "documentation": "/api/v1/scholar/info/"
}
```

### Invalid Format

```json
{
  "error": "Invalid format: xml",
  "valid_formats": ["json", "bibtex", "csv", "text"]
}
```

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

## API Info Endpoint

Get API documentation and status:

```
GET {{ api_base_url }}/api/v1/scholar/info/
```

Returns full API documentation including all parameters, examples, and current rate limits.

## Python Example

```python
import requests

# Basic search
response = requests.get(
    "{{ api_base_url }}/api/v1/scholar/search/",
    params={"q": "neural networks", "limit": 10}
)
data = response.json()

for paper in data["results"]:
    print(f"{paper['title']} ({paper['year']}) - {paper['citations']} citations")

# With API key
response = requests.get(
    "{{ api_base_url }}/api/v1/scholar/search/",
    params={"q": "deep learning", "format": "json"},
    headers={"X-SCITEX-API-KEY": "your-api-key"}
)
```

## JavaScript Example

```javascript
// Basic search
const response = await fetch(
  "{{ api_base_url }}/api/v1/scholar/search/?q=neural+networks&limit=10"
);
const data = await response.json();

data.results.forEach(paper => {
  console.log(`${paper.title} (${paper.year}) - ${paper.citations} citations`);
});

// With API key
const response = await fetch(
  "{{ api_base_url }}/api/v1/scholar/search/?q=deep+learning",
  {
    headers: { "X-SCITEX-API-KEY": "your-api-key" }
  }
);
```
