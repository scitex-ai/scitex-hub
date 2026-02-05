# Quick Start

Get started with the SciTeX Scholar API in minutes.

## Your First Search

Search for papers about "machine learning":

```bash
curl "{{ api_base_url }}/api/v1/scholar/search/?q=machine+learning"
```

## Limit Results

Get only 10 results:

```bash
curl "{{ api_base_url }}/api/v1/scholar/search/?q=machine+learning&limit=10"
```

## Choose Sources

Search only PubMed and arXiv:

```bash
curl "{{ api_base_url }}/api/v1/scholar/search/?q=cancer&sources=pubmed,arxiv"
```

## Export to BibTeX

Download references for your paper:

```bash
curl "{{ api_base_url }}/api/v1/scholar/search/?q=deep+learning&format=bibtex" \
  -o references.bib
```

## Export to CSV

Download for spreadsheet analysis:

```bash
curl "{{ api_base_url }}/api/v1/scholar/search/?q=covid-19&format=csv" \
  -o papers.csv
```

## Python Example

```python
import requests

# Search
response = requests.get(
    "{{ api_base_url }}/api/v1/scholar/search/",
    params={
        "q": "neural networks",
        "limit": 10,
        "sources": "pubmed,arxiv,semantic"
    }
)
data = response.json()

# Print results
print(f"Found {data['total_count']} papers")
for paper in data['results'][:5]:
    print(f"- {paper['title']} ({paper['year']}) - {paper['citations']} citations")
```

## JavaScript Example

```javascript
const params = new URLSearchParams({
  q: "neural networks",
  limit: 10,
  sources: "pubmed,arxiv,semantic"
});

const response = await fetch(
  `{{ api_base_url }}/api/v1/scholar/search/?${params}`
);
const data = await response.json();

console.log(`Found ${data.total_count} papers`);
data.results.slice(0, 5).forEach(paper => {
  console.log(`- ${paper.title} (${paper.year}) - ${paper.citations} citations`);
});
```

## Common Parameters

| Parameter | Example | Description |
|-----------|---------|-------------|
| `q` | `machine+learning` | Search query (required) |
| `limit` | `50` | Max results per source (default: 20, max: 100) |
| `format` | `bibtex` | Output format: json, bibtex, csv, text |
| `sources` | `pubmed,arxiv` | Data sources to search |

## Available Sources

| Source | Description |
|--------|-------------|
| `pubmed` | Biomedical literature |
| `arxiv` | Physics, math, CS preprints |
| `semantic` | Semantic Scholar |
| `crossref` | DOI metadata |
| `openalex` | Open scholarly metadata |

## Next Steps

- [API Reference](../api/scholar.md) - Full parameter documentation
- [Export Formats](../guides/export-formats.md) - Detailed format examples
- [Authentication](../guides/authentication.md) - Get higher rate limits
