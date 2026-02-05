# Export Formats

The Scholar Search API supports multiple export formats for different use cases.

## Available Formats

| Format | Content-Type | Use Case |
|--------|--------------|----------|
| `json` | application/json | Programmatic access |
| `bibtex` | application/x-bibtex | Citation managers |
| `csv` | text/csv | Spreadsheets, data analysis |
| `text` | text/plain | Quick reading, sharing |

## JSON Format (Default)

Best for programmatic access and data processing.

```bash
curl "{{ api_base_url }}/api/v1/scholar/search/?q=machine+learning&format=json"
```

### Response Structure

```json
{
  "status": "success",
  "query": "machine learning",
  "total_count": 60,
  "sources": {
    "pubmed": {"count": 20, "status": "success"},
    "arxiv": {"count": 20, "status": "success"},
    "semantic": {"count": 20, "status": "success"}
  },
  "results": [
    {
      "title": "Paper Title",
      "authors": "Author One, Author Two",
      "journal": "Journal Name",
      "year": "2024",
      "doi": "10.1234/example",
      "pmid": "",
      "arxiv_id": "",
      "citations": 150,
      "impact_factor": 5.2,
      "is_open_access": true,
      "abstract": "Paper abstract...",
      "url": "https://doi.org/10.1234/example",
      "source": "semantic"
    }
  ]
}
```

## BibTeX Format

Best for citation managers like Zotero, Mendeley, or LaTeX.

```bash
curl "{{ api_base_url }}/api/v1/scholar/search/?q=deep+learning&format=bibtex" \
  -o references.bib
```

### Response Example

```bibtex
@article{author2024paper,
  author = {Author One, Author Two},
  title = {Paper Title},
  journal = {Journal Name},
  year = {2024},
  doi = {10.1234/example},
  citations = {150},
  impactfactor = {5.2},
  abstract = {Paper abstract...},
}

@article{another2023study,
  author = {Another Author},
  title = {Another Study},
  journal = {Another Journal},
  year = {2023},
  doi = {10.5678/another},
  citations = {75},
  impactfactor = {3.8},
}
```

### Custom BibTeX Fields

SciTeX includes additional fields for bibliometric analysis:

| Field | Description |
|-------|-------------|
| `citations` | Citation count |
| `impactfactor` | Journal impact factor |
| `abstract` | Paper abstract (truncated to 500 chars) |

## CSV Format

Best for spreadsheets and data analysis.

```bash
curl "{{ api_base_url }}/api/v1/scholar/search/?q=covid&format=csv" \
  -o papers.csv
```

### Columns

| Column | Description |
|--------|-------------|
| Title | Paper title |
| Authors | Author names |
| Journal | Journal name |
| Year | Publication year |
| DOI | Digital Object Identifier |
| PMID | PubMed ID |
| arXiv ID | arXiv identifier |
| Citations | Citation count |
| Impact Factor | Journal impact factor |
| Open Access | Yes/No |
| Source | Data source |
| URL | Link to paper |
| Abstract | Paper abstract |

## Plain Text Format

Best for quick reading and sharing.

```bash
curl "{{ api_base_url }}/api/v1/scholar/search/?q=neural+networks&format=text"
```

### Response Example

```
[1] Paper Title
Authors: Author One, Author Two
Journal: Journal Name
Year: 2024
Citations: 150
Impact Factor: 5.2
DOI: 10.1234/example
URL: https://doi.org/10.1234/example
Abstract: Paper abstract truncated to 300 characters...

---

[2] Another Paper
Authors: Another Author
Journal: Another Journal
Year: 2023
Citations: 75
Impact Factor: 3.8
DOI: 10.5678/another
URL: https://doi.org/10.5678/another
Abstract: Another abstract...
```

## Choosing the Right Format

| Use Case | Recommended Format |
|----------|-------------------|
| Building an application | JSON |
| Writing a paper | BibTeX |
| Analyzing trends | CSV |
| Quick review | Text |
| Sharing with colleagues | BibTeX or Text |
