#!/bin/bash
set -euo pipefail

if [ "${SCITEX_APPS_PYTHON_MODE:-}" != "image-only" ]; then
    echo "ERROR: /image-runtime.sh requires SCITEX_APPS_PYTHON_MODE=image-only" >&2
    exit 2
fi

# The verifier and policy inputs are root-owned under /opt, but dependency
# imports must run with the same privileges as the application process.
gosu scitex python /opt/scitex-image-contract/scripts/deploy/verify_image_dependency_contract.py

# Celery services do not need root-init's web-only UID/volume repairs. Drop
# privileges before the shared application entrypoint and service command.
exec gosu scitex "$@"
