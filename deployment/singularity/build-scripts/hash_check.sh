#!/bin/bash
# File: ./deployment/singularity/build/hash_check.sh
# ============================================
# Hash-based rebuild detection
# ============================================
# Sourced by build.sh -- do not run directly.
# Expects: GREEN, YELLOW, NC (from common.sh)

# Compute composite hash from def file content and optional extra string.
# Usage: compute_hash <def_file> [extra_string]
compute_hash() {
    local def_file="$1"
    local extra="${2:-}"
    local def_hash
    def_hash=$(sha256sum "$def_file" | awk '{print $1}')
    echo "${def_hash} ${extra}" | sha256sum | awk '{print $1}'
}

# Check if a rebuild is needed.
# Returns 0 (true) if rebuild needed, 1 (false) if up-to-date.
# Usage: needs_rebuild <force> <sif_file> <hash_file> <current_hash> <label>
needs_rebuild() {
    local force="$1"
    local sif_file="$2"
    local hash_file="$3"
    local current_hash="$4"
    local label="$5"

    if [ "$force" = true ]; then
        echo -e "${YELLOW}Force rebuild requested${NC}"
        return 0
    fi

    if [ ! -f "$sif_file" ]; then
        echo -e "${YELLOW}No ${label} SIF found -- initial build${NC}"
        return 0
    fi

    if [ ! -f "$hash_file" ]; then
        echo -e "${YELLOW}No hash record -- rebuild needed${NC}"
        return 0
    fi

    local stored_hash
    stored_hash=$(cat "$hash_file" 2>/dev/null || echo "")
    if [ "$current_hash" = "$stored_hash" ]; then
        local sif_size sif_date
        sif_size=$(du -h "$sif_file" | cut -f1)
        sif_date=$(date -r "$sif_file" "+%Y-%m-%d %H:%M")
        echo -e "${GREEN}${label} SIF is up-to-date${NC}"
        echo -e "   Image: $(basename "$sif_file") (${sif_size}, built ${sif_date})"
        echo -e "   Hash:  ${current_hash:0:12}..."
        echo -e "   Use ${YELLOW}--force${NC} to rebuild anyway"
        return 1
    fi

    echo -e "${YELLOW}Definition or versions changed -- rebuild needed${NC}"
    echo -e "   Old hash: ${stored_hash:0:12}..."
    echo -e "   New hash: ${current_hash:0:12}..."
    return 0
}

# Save hash after successful build.
# Usage: save_hash <hash_file> <hash_value>
save_hash() {
    echo "$2" >"$1"
}

# EOF
