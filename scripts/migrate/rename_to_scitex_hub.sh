#!/usr/bin/env bash
# scripts/migrate/rename_to_scitex_hub.sh
#
# One-shot helper to migrate an existing scitex-cloud working tree and
# deployment into the v0.18.0 scitex-hub layout.
#
# Idempotent: re-running after a partial migration finishes the rest;
# already-renamed paths are skipped.
#
# Steps performed (in order):
#   1. rename ~/proj/scitex-cloud  ->  ~/proj/scitex-hub (with a back symlink)
#   2. set the git remote to the new repo URL (relies on GitHub redirect
#      until the rename is verified, then switches to the canonical name)
#   3. rewrite every SCITEX_CLOUD_* -> SCITEX_HUB_* in deployment/.env files
#   4. print a final docker-compose restart hint
#
# Read the script before running it.

set -euo pipefail

OLD_DIR="${OLD_DIR:-$HOME/proj/scitex-cloud}"
NEW_DIR="${NEW_DIR:-$HOME/proj/scitex-hub}"
NEW_REMOTE="${NEW_REMOTE:-https://github.com/ywatanabe1989/scitex-hub.git}"

log() { printf '\033[36m[migrate]\033[0m %s\n' "$*"; }
warn() { printf '\033[33m[migrate]\033[0m %s\n' "$*" >&2; }
die() { printf '\033[31m[migrate]\033[0m %s\n' "$*" >&2; exit 1; }

# --- 1. directory rename ---
if [[ -d "$OLD_DIR" && ! -L "$OLD_DIR" && ! -e "$NEW_DIR" ]]; then
    log "rename $OLD_DIR -> $NEW_DIR"
    mv "$OLD_DIR" "$NEW_DIR"
    log "create back-compat symlink $OLD_DIR -> $NEW_DIR"
    ln -s "$NEW_DIR" "$OLD_DIR"
elif [[ -L "$OLD_DIR" && -d "$NEW_DIR" ]]; then
    log "already renamed (symlink + new dir present); skipping"
elif [[ -L "$NEW_DIR" && -d "$OLD_DIR" ]]; then
    warn "$NEW_DIR is a symlink pointing into $OLD_DIR — replacing with a real dir move"
    rm -f "$NEW_DIR"
    mv "$OLD_DIR" "$NEW_DIR"
    ln -s "$NEW_DIR" "$OLD_DIR"
else
    warn "neither $OLD_DIR nor $NEW_DIR matches expected pattern; skipping directory move"
fi

cd "$NEW_DIR" 2>/dev/null || die "cannot cd into $NEW_DIR"

# --- 2. git remote ---
current="$(git -C "$NEW_DIR" remote get-url origin 2>/dev/null || true)"
if [[ "$current" == *"scitex-cloud"* ]]; then
    log "git remote: $current -> $NEW_REMOTE"
    git -C "$NEW_DIR" remote set-url origin "$NEW_REMOTE"
else
    log "git remote already up to date ($current)"
fi

# --- 3. env files ---
shopt -s nullglob
env_files=( deployment/docker/envs/.env.* deployment/envs/.env.* )
shopt -u nullglob

if (( ${#env_files[@]} == 0 )); then
    warn "no deployment .env files found; skipping env rename"
else
    for f in "${env_files[@]}"; do
        if grep -q 'SCITEX_CLOUD_' "$f" 2>/dev/null; then
            log "rewriting SCITEX_CLOUD_* -> SCITEX_HUB_* in $f"
            sed -i 's/SCITEX_CLOUD_/SCITEX_HUB_/g' "$f"
        else
            log "no SCITEX_CLOUD_ entries in $f; skipping"
        fi
    done
fi

# --- 4. restart hint ---
cat <<'EOF'

migration complete. Next steps:
    cd ~/proj/scitex-hub
    make ENV=dev down
    make ENV=dev up

If anything broke, the snapshot tag `pre-rename-cloud-to-hub`
(commit 379018c4) is the pre-rename state; check it out in a worktree
to inspect.
EOF
