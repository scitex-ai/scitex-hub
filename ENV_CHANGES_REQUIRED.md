# Environment Variable Changes Required

After pulling this branch, manually update your `.env` files:

## SECRET/.env.dev
```bash
# Add these lines after SCITEX_SCHOLAR_PUBMED_EMAIL:
# SciTeX Scholar - CrossRef API Endpoints
SCITEX_SCHOLAR_CROSSREF_API_URL_DEV=http://169.254.11.50:3333
SCITEX_SCHOLAR_CROSSREF_API_URL_NAS=http://crossref:3333
# Active endpoint for DEV environment (points to NAS over local network)
SCITEX_SCHOLAR_CROSSREF_API_URL=${SCITEX_SCHOLAR_CROSSREF_API_URL_DEV}
```

## SECRET/.env.nas
```bash
# Add these lines after SCITEX_SCHOLAR_PUBMED_EMAIL:
# SciTeX Scholar - CrossRef API Endpoints
SCITEX_SCHOLAR_CROSSREF_API_URL_DEV=http://169.254.11.50:3333
SCITEX_SCHOLAR_CROSSREF_API_URL_NAS=http://crossref:3333
# Active endpoint for NAS environment (internal Docker network)
SCITEX_SCHOLAR_CROSSREF_API_URL=${SCITEX_SCHOLAR_CROSSREF_API_URL_NAS}
```
