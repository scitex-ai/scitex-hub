#!/usr/bin/env bash
# docker-memory-limits.sh -- Review and apply Docker container memory limits
# Run on the NAS
set -euo pipefail

# --- Configuration ---
# Default memory limit per container (adjust as needed)
DEFAULT_MEM_LIMIT="2g"
# Compose file locations to scan
COMPOSE_DIRS=(
    "/opt/scitex"
    "/opt/docker"
    "$HOME"
)

echo "========================================"
echo " Docker Memory Limits Checker"
echo "========================================"
echo ""

# --- Show current container memory usage ---
echo "--- Current container memory usage ---"
docker stats --no-stream --format "table {{.Name}}\t{{.MemUsage}}\t{{.MemPerc}}\t{{.PIDs}}" 2>/dev/null || {
    echo "ERROR: Cannot reach Docker daemon."
    exit 1
}
echo ""

# --- Show total system memory ---
TOTAL_MEM=$(free -h | awk '/^Mem:/{print $2}')
AVAIL_MEM=$(free -h | awk '/^Mem:/{print $7}')
echo "System memory: ${TOTAL_MEM} total, ${AVAIL_MEM} available"
echo ""

# --- Find compose files ---
echo "--- Scanning for docker-compose files ---"
COMPOSE_FILES=()
for dir in "${COMPOSE_DIRS[@]}"; do
    if [ -d "$dir" ]; then
        while IFS= read -r f; do
            COMPOSE_FILES+=("$f")
        done < <(find "$dir" -maxdepth 3 -name "docker-compose*.yml" -o -name "compose*.yml" 2>/dev/null)
    fi
done

if [ ${#COMPOSE_FILES[@]} -eq 0 ]; then
    echo "No docker-compose files found in: ${COMPOSE_DIRS[*]}"
    echo "Checking running containers for memory limits instead..."
    echo ""

    echo "--- Containers WITHOUT memory limits ---"
    for cid in $(docker ps -q); do
        NAME=$(docker inspect --format '{{.Name}}' "$cid" | sed 's/^\///')
        MEM_LIMIT=$(docker inspect --format '{{.HostConfig.Memory}}' "$cid")
        if [ "$MEM_LIMIT" = "0" ]; then
            echo "  [NO LIMIT] $NAME"
        else
            MEM_MB=$((MEM_LIMIT / 1024 / 1024))
            echo "  [${MEM_MB}MB]    $NAME"
        fi
    done
    echo ""
    echo "To set limits, add mem_limit to your docker-compose.yml services:"
    echo ""
    echo "  services:"
    echo "    myservice:"
    echo "      mem_limit: ${DEFAULT_MEM_LIMIT}"
    echo "      memswap_limit: ${DEFAULT_MEM_LIMIT}"
    exit 0
fi

for cf in "${COMPOSE_FILES[@]}"; do
    echo ""
    echo "File: $cf"

    if grep -q "mem_limit" "$cf"; then
        echo "  [OK] Has memory limits defined"
        grep -n "mem_limit" "$cf" | sed 's/^/    /'
    else
        echo "  [MISSING] No mem_limit found"
        echo ""
        echo "  Suggested additions for each service in $cf:"
        echo "    mem_limit: ${DEFAULT_MEM_LIMIT}"
        echo "    memswap_limit: ${DEFAULT_MEM_LIMIT}"
        echo ""

        read -r -p "  Apply default ${DEFAULT_MEM_LIMIT} limit to all services? [y/N] " REPLY </dev/tty 2>/dev/null || REPLY="n"
        if [[ "$REPLY" =~ ^[Yy]$ ]]; then
            # Backup first
            cp "$cf" "${cf}.bak.$(date +%Y%m%d%H%M%S)"
            echo "  Backed up to ${cf}.bak.*"

            # Insert mem_limit after each 'image:' or 'build:' line
            sed -i '/^\([[:space:]]*\)\(image:\|build:\)/a\      mem_limit: '"${DEFAULT_MEM_LIMIT}"'\n      memswap_limit: '"${DEFAULT_MEM_LIMIT}" "$cf"
            echo "  Applied memory limits. Review the file before restarting."
        fi
    fi
done

echo ""
echo "--- Next steps ---"
echo "1. Review the compose files above"
echo "2. Restart containers: docker compose -f <file> up -d"
echo "3. Verify with: docker stats --no-stream"
