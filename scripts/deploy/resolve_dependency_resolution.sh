#!/bin/bash
# Resolve the committed, deterministic dependency refresh input.
set -euo pipefail

ENVIRONMENT="${1:-}"
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
NONCE_FILE="${SCITEX_HUB_DEPENDENCY_RESOLUTION_FILE:-$PROJECT_ROOT/deployment/docker/dependency-resolution.nonce}"

case "$ENVIRONMENT" in
    prod|staging)
        if [ ! -s "$NONCE_FILE" ]; then
            echo "Error: release dependency-resolution input is missing: $NONCE_FILE" >&2
            exit 1
        fi
        ;;
    dev)
        if [ ! -s "$NONCE_FILE" ]; then
            printf '%s\n' dev
            exit 0
        fi
        ;;
    *)
        echo "Usage: $0 <dev|staging|prod>" >&2
        exit 2
        ;;
esac

NONCE="$(tr -d '\r\n' < "$NONCE_FILE")"
case "$NONCE" in
    ""|*[!A-Za-z0-9._-]*)
        echo "Error: dependency-resolution input must match [A-Za-z0-9._-]+" >&2
        exit 1
        ;;
esac
printf '%s\n' "$NONCE"
