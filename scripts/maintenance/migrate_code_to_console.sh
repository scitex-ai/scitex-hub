#!/bin/bash
# ==============================================================================
# migrate_code_to_console.sh - Migrate code_app to console_app in user data
# ==============================================================================
# Migrates existing user workspaces and Gitea repositories from:
#   - scitex/code/ → scitex/console/
#   - Gitea repo names: *-code → *-console
#
# Usage:
#   ./scripts/maintenance/migrate_code_to_console.sh [--dry-run]
#
# ==============================================================================

set -e

# Colors
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
CYAN='\033[0;36m'
NC='\033[0m'

# Get script directory and project root
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

# Parse arguments
DRY_RUN=false
if [ "$1" = "--dry-run" ]; then
    DRY_RUN=true
    echo -e "${CYAN}🔍 DRY RUN MODE - No changes will be made${NC}\n"
fi

# Counters
USERS_MIGRATED=0
GITEA_REPOS_MIGRATED=0
TEMPLATES_MIGRATED=0

echo -e "${CYAN}=== SciTeX Code → Console Migration ===${NC}\n"

# =============================================================================
# 1. Migrate template directory
# =============================================================================
echo -e "${CYAN}[1/3] Migrating project template...${NC}"

TEMPLATE_CODE="$PROJECT_ROOT/templates/research-master/scitex/code"
TEMPLATE_CONSOLE="$PROJECT_ROOT/templates/research-master/scitex/console"

if [ -d "$TEMPLATE_CODE" ]; then
    if [ "$DRY_RUN" = true ]; then
        echo -e "${YELLOW}  Would rename: $TEMPLATE_CODE → $TEMPLATE_CONSOLE${NC}"
    else
        # Use sudo only if not root
        if [ "$(id -u)" -eq 0 ]; then
            mv "$TEMPLATE_CODE" "$TEMPLATE_CONSOLE"
        else
            sudo mv "$TEMPLATE_CODE" "$TEMPLATE_CONSOLE"
        fi
        echo -e "${GREEN}  ✓ Renamed template: code/ → console/${NC}"
        ((TEMPLATES_MIGRATED++))
    fi
else
    echo -e "${GREEN}  ✓ Template already migrated or doesn't exist${NC}"
fi

# =============================================================================
# 2. Migrate user workspace directories
# =============================================================================
echo -e "\n${CYAN}[2/3] Migrating user workspaces...${NC}"

USER_DATA_DIR="$PROJECT_ROOT/data/users"

if [ ! -d "$USER_DATA_DIR" ]; then
    echo -e "${YELLOW}  No user data directory found${NC}"
else
    # Temporarily disable exit-on-error for migration loop
    set +e

    # Find all users with scitex/code/ directories
    while IFS= read -r -d '' code_dir; do
        username=$(basename "$(dirname "$(dirname "$(dirname "$code_dir")")")")
        project=$(basename "$(dirname "$(dirname "$code_dir")")")
        console_dir="${code_dir/\/code/\/console}"

        if [ "$DRY_RUN" = true ]; then
            echo -e "${YELLOW}  Would migrate: $username/$project/scitex/code/ → scitex/console/${NC}"
        else
            # Use sudo only if not root
            if [ "$(id -u)" -eq 0 ]; then
                mv "$code_dir" "$console_dir" 2>/dev/null
            else
                sudo mv "$code_dir" "$console_dir" 2>/dev/null
            fi

            # Check if migration succeeded
            if [ -d "$console_dir" ]; then
                echo -e "${GREEN}  ✓ Migrated: $username/$project/scitex/code/ → scitex/console/${NC}"
                ((USERS_MIGRATED++))
            else
                echo -e "${YELLOW}  ⚠ Failed: $username/$project/scitex/code/ (may already be migrated)${NC}"
            fi
        fi
    done < <(find "$USER_DATA_DIR" -type d -path "*/scitex/code" -print0 2>/dev/null)

    # Re-enable exit-on-error
    set -e

    if [ "$USERS_MIGRATED" -eq 0 ] && [ "$DRY_RUN" = false ]; then
        echo -e "${GREEN}  ✓ No user workspaces to migrate${NC}"
    fi

    # Create console/ directory from template for projects that don't have it
    echo -e "\n${CYAN}Creating console/ for projects without it...${NC}"
    TEMPLATE_CONSOLE_DIR="$PROJECT_ROOT/templates/research-master/scitex/console"
    CREATED=0

    if [ -d "$TEMPLATE_CONSOLE_DIR" ]; then
        # Find all projects with scitex/ but no console/ subdirectory
        while IFS= read -r -d '' scitex_dir; do
            if [ ! -d "$scitex_dir/console" ]; then
                username=$(basename "$(dirname "$(dirname "$scitex_dir")")")
                project=$(basename "$(dirname "$scitex_dir")")

                if [ "$DRY_RUN" = true ]; then
                    echo -e "${YELLOW}  Would create: $username/$project/scitex/console/ from template${NC}"
                else
                    # Use sudo/root depending on environment
                    if [ "$(id -u)" -eq 0 ]; then
                        cp -r "$TEMPLATE_CONSOLE_DIR" "$scitex_dir/console"
                    else
                        sudo cp -r "$TEMPLATE_CONSOLE_DIR" "$scitex_dir/console"
                    fi

                    if [ -d "$scitex_dir/console" ]; then
                        echo -e "${GREEN}  ✓ Created: $username/$project/scitex/console/${NC}"
                        ((CREATED++))
                    fi
                fi
            fi
        done < <(find "$USER_DATA_DIR" -type d -name "scitex" -path "*/proj/*/scitex" -print0 2>/dev/null)

        if [ "$CREATED" -gt 0 ]; then
            echo -e "${GREEN}  ✓ Created $CREATED console directories${NC}"
        elif [ "$DRY_RUN" = false ]; then
            echo -e "${GREEN}  ✓ All projects already have console/ directory${NC}"
        fi
    else
        echo -e "${YELLOW}  ⚠ Template console/ directory not found, skipping creation${NC}"
    fi
fi

# =============================================================================
# 3. Migrate Gitea repository names (if Gitea is running)
# =============================================================================
echo -e "\n${CYAN}[3/3] Checking Gitea repositories...${NC}"

# Check if Gitea container is running
if docker ps --filter "name=scitex-hub.*gitea" --format "{{.Names}}" | grep -q gitea; then
    GITEA_CONTAINER=$(docker ps --filter "name=scitex-hub.*gitea" --format "{{.Names}}" | head -1)

    # Get all repos ending with -code
    REPOS=$(docker exec "$GITEA_CONTAINER" gitea admin repo list 2>/dev/null | grep -E '/.*-code$' || true)

    if [ -n "$REPOS" ]; then
        echo "$REPOS" | while IFS= read -r repo; do
            owner=$(echo "$repo" | cut -d'/' -f1)
            old_name=$(echo "$repo" | cut -d'/' -f2)
            new_name="${old_name%-code}-console"

            if [ "$DRY_RUN" = true ]; then
                echo -e "${YELLOW}  Would rename Gitea repo: $owner/$old_name → $owner/$new_name${NC}"
            else
                # Rename repo via Gitea API (requires admin token)
                echo -e "${YELLOW}  ⚠ Gitea repo rename requires manual action via web UI or API${NC}"
                echo -e "    Rename: $owner/$old_name → $owner/$new_name"
                # Note: Gitea CLI doesn't have rename command, must use API or web UI
            fi
        done
    else
        echo -e "${GREEN}  ✓ No Gitea repos with -code suffix found${NC}"
    fi
else
    echo -e "${YELLOW}  ⚠ Gitea container not running, skipping repository migration${NC}"
fi

# =============================================================================
# Summary
# =============================================================================
echo -e "\n${CYAN}=== Migration Summary ===${NC}"
echo -e "  Templates migrated: ${GREEN}$TEMPLATES_MIGRATED${NC}"
echo -e "  User workspaces migrated: ${GREEN}$USERS_MIGRATED${NC}"
echo -e "  Gitea repos (manual): ${YELLOW}$GITEA_REPOS_MIGRATED${NC}"

if [ "$DRY_RUN" = true ]; then
    echo -e "\n${CYAN}💡 Run without --dry-run to apply changes${NC}"
else
    echo -e "\n${GREEN}✅ Migration complete${NC}"
fi
