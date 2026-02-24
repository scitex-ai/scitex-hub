#!/bin/bash
# File: ./deployment/singularity/build/versions_json.sh
# ============================================
# Update versions.json with build metadata
# ============================================
# Sourced by build.sh -- do not run directly.
# Expects: YELLOW, NC (from common.sh)

# Update or create versions.json after a successful final build.
# Usage: update_versions_json <json_file> <scitex_ver> <base_ver> \
#            <build_date> <build_time> <sif_size> <def_hash> <pypi_versions>
update_versions_json() {
    local json_file="$1"
    local scitex_ver="$2"
    local base_ver="$3"
    local build_date="$4"
    local build_time="$5"
    local sif_size="$6"
    local def_hash="$7"
    local pypi_versions="$8"

    python3 -c "
import json, os

vf = '$json_file'
try:
    with open(vf) as f:
        data = json.load(f)
except (json.JSONDecodeError, FileNotFoundError, OSError):
    data = {'builds': []}

if 'builds' not in data:
    data['builds'] = []

data['current'] = 'scitex-v${scitex_ver}.sif'
data['base'] = 'scitex-base-v${base_ver}.sif'

# Remove duplicate entry for same version
data['builds'] = [b for b in data['builds'] if b.get('version') != '${scitex_ver}']

data['builds'].append({
    'version': '${scitex_ver}',
    'sif': 'scitex-v${scitex_ver}.sif',
    'base_version': '${base_ver}',
    'build_date': '${build_date}',
    'build_time': '${build_time}',
    'size': '${sif_size}',
    'def_hash': '${def_hash}',
    'pypi_versions': '${pypi_versions}'
})

with open(vf, 'w') as f:
    json.dump(data, f, indent=2)
    f.write('\n')
" 2>/dev/null || echo -e "${YELLOW}Warning: Could not update versions.json${NC}"
}

# EOF
