#!/bin/bash
# Install the complete workspace graph after development source mounts exist.
set -euo pipefail
app_root="${1:?Usage: install_dev_frontend.sh <application-root>}"
test -f "$app_root/package.json"
python "$(dirname -- "${BASH_SOURCE[0]}")/install_dev_frontend.py" "$app_root"
