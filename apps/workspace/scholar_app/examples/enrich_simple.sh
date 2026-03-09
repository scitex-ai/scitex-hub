#!/bin/bash
# File: apps/scholar_app/examples/enrich_simple.sh
# Simple one-call BibTeX enrichment via API
#
# Usage:
#   export SCITEX_API_KEY="scitex_your_key_here"
#   ./enrich_simple.sh -i input.bib -o output.bib
#   or
#   ./enrich_simple.sh -i input.bib  # outputs to input-enriched.bib

set -e

# Default values
INPUT_FILE=""
OUTPUT_FILE=""
USE_CACHE="true"
BASE_URL="${SCITEX_BASE_URL:-http://127.0.0.1:8000}"

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        -i)
            INPUT_FILE="$2"
            shift 2
            ;;
        -o)
            OUTPUT_FILE="$2"
            shift 2
            ;;
        --no-cache)
            USE_CACHE="false"
            shift
            ;;
        *)
            echo "Unknown option: $1"
            echo "Usage: $0 -i input.bib [-o output.bib] [--no-cache]"
            exit 1
            ;;
    esac
done

# Validation
if [ -z "$SCITEX_API_KEY" ]; then
    echo "Error: SCITEX_API_KEY not set"
    echo "Get your key from: ${BASE_URL}/scholar/api-keys/"
    echo "Then run: export SCITEX_API_KEY='scitex_your_key_here'"
    exit 1
fi

if [ -z "$INPUT_FILE" ] || [ ! -f "$INPUT_FILE" ]; then
    echo "Usage: $0 -i <input.bib> [-o <output.bib>] [--no-cache]"
    echo ""
    echo "Options:"
    echo "  -i <file>      Input BibTeX file (required)"
    echo "  -o <file>      Output file (default: input-enriched.bib)"
    echo "  --no-cache     Disable cache (force fresh metadata fetch)"
    exit 1
fi

# Set default output filename if not specified
if [ -z "$OUTPUT_FILE" ]; then
    OUTPUT_FILE="${INPUT_FILE%.bib}-enriched.bib"
fi

echo "Enriching: $INPUT_FILE"
echo "Output: $OUTPUT_FILE"
echo "Cache: $USE_CACHE"
echo ""

# Single synchronous API call
curl -X POST "${BASE_URL}/scholar/api/bibtex/enrich/" \
    -H "Authorization: Bearer ${SCITEX_API_KEY}" \
    -F "bibtex_file=@${INPUT_FILE}" \
    -F "use_cache=${USE_CACHE}" \
    -o "$OUTPUT_FILE" \
    --progress-bar

if [ -f "$OUTPUT_FILE" ] && [ -s "$OUTPUT_FILE" ]; then
    echo ""
    echo "✓ Enrichment complete: $OUTPUT_FILE"
else
    echo ""
    echo "✗ Enrichment failed"
    exit 1
fi

# EOF
