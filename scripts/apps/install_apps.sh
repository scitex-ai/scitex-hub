#!/usr/bin/env bash
# Install workspace apps declared in .scitex-apps.json.
#
# Ensures app repos exist as siblings so Vite's bridge discovery
# can scan them. Clones from git_url if the sibling is absent.
#
# Fast-path (2026-07-10): siblings track a live branch (git_ref, e.g.
# "develop") for ywatanabe's editable/developmental dev-install feature.
# Previously this script unconditionally cloned + `pip install -e` +
# `npm install` all N siblings on EVERY container boot/restart — 10+
# minutes, blocking daphne from ever binding its port (confirmed live
# during the 2026-07-09 staging rebuild; see hub-postboot-warmup-window).
# It now does a cheap `git ls-remote` freshness check per sibling and
# only pays for clone/pip/npm when something has actually changed:
#
#   - sibling dir missing                    -> full clone (unavoidable)
#   - local checkout dirty or diverged        -> leave untouched (never
#     from our own last-synced baseline         clobber in-progress
#                                                editable-dev work)
#   - clean + matches our last-synced baseline
#     + remote unchanged                      -> skip entirely
#   - clean + matches baseline + remote moved -> fast-forward (fetch +
#                                                 reset), re-run pip install
#   - pip package doesn't resolve to THIS     -> (re)install. Catches the
#     exact checkout                             case where a persistent
#                                                 /app/.apps volume kept the
#                                                 git checkout across a
#                                                 rebuild, but the fresh
#                                                 image reset site-packages
#                                                 to the Dockerfile-pinned
#                                                 PyPI version.
#   - npm: mtime-gated per package.json found, mirroring the existing
#     app-root idiom ([ ! -d node_modules ] ||
#     [ package.json -nt node_modules/.install-timestamp ]).
#
# A flock-guarded critical section serializes concurrent runs: this
# script is invoked, UNGUARDED for celery, by THREE containers that share
# the same /app/.apps volume (django, celery_worker, celery_beat — see
# deployment/docker/common/scripts/entrypoint-prod.sh). Without the lock,
# simultaneous boots could race to clone into the same target directory.
# In the common case, whichever container acquires the lock first pays
# the real cost once; the other two then see "already satisfied" and
# return almost immediately.
#
# Usage:
#   bash scripts/apps/install_apps.sh          # auto: use sibling if present, clone if not
#   bash scripts/apps/install_apps.sh --clone   # force clone (for CI)

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
PARENT_DIR="$(cd "$PROJECT_ROOT/.." && pwd)"
REGISTRY="$PROJECT_ROOT/.scitex-apps.json"

# In Docker, PARENT_DIR is / (not writable). Fall back to .apps/ inside project.
if [[ "$PARENT_DIR" == "/" ]] || [[ ! -w "$PARENT_DIR" ]]; then
    PARENT_DIR="$PROJECT_ROOT/.apps"
    mkdir -p "$PARENT_DIR"
fi

FORCE_CLONE=false
if [[ "${1:-}" == "--clone" ]]; then
    FORCE_CLONE=true
fi

if [[ ! -f "$REGISTRY" ]]; then
    echo "ERROR: $REGISTRY not found" >&2
    exit 1
fi

# Requires jq for JSON parsing
if ! command -v jq &>/dev/null; then
    echo "ERROR: jq is required but not installed" >&2
    exit 1
fi

# ------------------------------------------------------------------
# Serialize concurrent installers. django + celery_worker + celery_beat
# all run this script (unconditionally — see entrypoint-prod.sh) against
# the SAME /app/.apps volume. Without a lock, two containers booting at
# the same instant could both see "dir absent" and clone into it
# concurrently, corrupting the checkout. Best-effort: a missing `flock`
# degrades to a warning rather than a hard failure.
# ------------------------------------------------------------------
LOCK_FILE="$PARENT_DIR/.install_apps.lock"
if command -v flock &>/dev/null; then
    # Braces are LOAD-BEARING: `exec 200>f 2>/dev/null` (no braces) would
    # make BOTH redirections permanent for the rest of the script — i.e.
    # discard every subsequent stderr line (uv/pip/git errors, the fatal
    # ERROR messages below...). With the brace group, fd 200 (opened by
    # exec) persists as intended while the 2>/dev/null applies only to
    # the group itself. This exact bug shipped in the first version of
    # this section and made PR #331's CI failure near-undiagnosable
    # (uv's "command not found" never appeared in the job log).
    if { exec 200>"$LOCK_FILE"; } 2>/dev/null; then
        if ! flock -w 600 200; then
            echo "WARNING: could not acquire $LOCK_FILE within 600s — proceeding without lock (risk of concurrent-boot race)" >&2
        fi
    else
        echo "WARNING: could not open $LOCK_FILE for locking — proceeding without lock" >&2
    fi
else
    echo "WARNING: flock not available — proceeding without concurrency lock" >&2
fi

APP_COUNT=$(jq '.apps | length' "$REGISTRY")
echo "Installing $APP_COUNT app(s) from $REGISTRY"

# Per-sibling bookkeeping: the sha WE last successfully synced this
# checkout to. Distinct from "current HEAD" so we can tell "local HEAD
# still matches what we last set it to" (safe to auto-update from
# upstream) from "something changed the checkout since then — e.g. a
# local commit, an interactive rebase, a hand-edit" (an editable-dev
# change in progress — never auto-touch it). Lives inside PARENT_DIR so
# it persists exactly as long as the checkouts do (same volume).
SYNC_STATE_DIR="$PARENT_DIR/.install-state"
mkdir -p "$SYNC_STATE_DIR"

# Prints the resolved remote sha for a branch/tag ref, or nothing if it
# can't be resolved (unreachable network, bad ref, ...). Never fails the
# caller — callers see an empty string and treat it as "couldn't check".
resolve_remote_sha() {
    local url="$1" ref="$2"
    git ls-remote "$url" "$ref" 2>/dev/null | awk 'NR==1{print $1}'
    return 0
}

for i in $(seq 0 $((APP_COUNT - 1))); do
    NAME=$(jq -r ".apps[$i].name" "$REGISTRY")
    GIT_URL=$(jq -r ".apps[$i].git_url" "$REGISTRY")
    GIT_REF=$(jq -r ".apps[$i].git_ref // \"develop\"" "$REGISTRY")
    PIP_PKG=$(jq -r ".apps[$i].pip_package // \"\"" "$REGISTRY")

    SIBLING_DIR="$PARENT_DIR/$NAME"
    # Computed up front (not after the clone block) so the pip-fallback
    # below always probes the CURRENT app's package name — see PR #329.
    PKG_NAME="${NAME//-/_}"
    SYNC_STATE_FILE="$SYNC_STATE_DIR/$NAME.sha"

    echo ""
    echo "--- $NAME ---"

    NEEDS_PIP=false

    if [[ ! -d "$SIBLING_DIR" ]]; then
        echo "Cloning $GIT_URL (ref: $GIT_REF) -> $SIBLING_DIR"
        if ! git clone --depth 1 --branch "$GIT_REF" "$GIT_URL" "$SIBLING_DIR" 2>&1; then
            echo "WARNING: Clone failed for $NAME — checking pip-installed package..."
            # Fall back to pip-installed package location
            PIP_STATIC=$(python3 -c "import importlib.util; spec = importlib.util.find_spec('${PKG_NAME}'); print(spec.submodule_search_locations[0] if spec else '')" 2>/dev/null || echo "")
            if [[ -n "$PIP_STATIC" ]] && [[ -d "$PIP_STATIC" ]]; then
                echo "Found pip-installed $NAME at $PIP_STATIC — symlinking"
                ln -sf "$(dirname "$(dirname "$PIP_STATIC")")" "$SIBLING_DIR"
            else
                echo "WARNING: $NAME not available via git or pip — Vite bridge will be incomplete"
            fi
        else
            NEEDS_PIP=true
            git -C "$SIBLING_DIR" rev-parse HEAD >"$SYNC_STATE_FILE" 2>/dev/null || true
        fi
    elif [[ "$FORCE_CLONE" == true ]]; then
        # CI's `--clone` means "ensure a checkout exists"; an existing one
        # is used exactly as-is (no fetch/pull) — unchanged from before.
        echo "Sibling exists but --clone forced; skipping clone, using existing"
    else
        echo "Sibling exists: $SIBLING_DIR"
        if ! git -C "$SIBLING_DIR" rev-parse --is-inside-work-tree &>/dev/null; then
            echo "Not a git checkout (symlink or plain dir) — skipping freshness check, using as-is"
        else
            LOCAL_SHA=$(git -C "$SIBLING_DIR" rev-parse HEAD 2>/dev/null || echo "")
            # Excludes build byproducts THIS SCRIPT ITSELF creates (uv's
            # editable install writes <pkg>.egg-info/ into the source tree;
            # npm writes package-lock.json / node_modules/) so a sibling
            # repo that doesn't already .gitignore them doesn't look
            # permanently "dirty" starting from its very first install —
            # which would silently wedge auto-sync forever after run #1.
            # Deliberately narrow (only known pip/npm side effects): a
            # genuinely new user-created file is NOT excluded here and
            # still correctly counts as dirty.
            DIRTY=$(git -C "$SIBLING_DIR" status --porcelain \
                -- . \
                ':(exclude)*.egg-info' ':(exclude)*.egg-info/**' \
                ':(exclude)node_modules' ':(exclude)node_modules/**' \
                ':(exclude)package-lock.json' \
                ':(exclude)__pycache__' ':(exclude)__pycache__/**' \
                ':(exclude)*.pyc' \
                2>/dev/null || echo "dirty-unknown")
            NO_BASELINE=true
            BASELINE_MATCHES=false
            if [[ -f "$SYNC_STATE_FILE" ]]; then
                NO_BASELINE=false
                if [[ "$(cat "$SYNC_STATE_FILE")" == "$LOCAL_SHA" ]]; then
                    BASELINE_MATCHES=true
                fi
            fi

            if [[ -n "$DIRTY" ]]; then
                echo "Uncommitted local changes present — leaving checkout untouched (editable-dev edit in progress)"
            elif [[ "$NO_BASELINE" == true ]] || [[ "$BASELINE_MATCHES" == true ]]; then
                # Either bootstrapping tracking for the first time (no
                # baseline recorded yet, e.g. a pre-existing checkout from
                # before this fix, or from the clone branch above) or we
                # have confirmed nothing has touched this checkout since we
                # last synced it — safe to check upstream.
                REMOTE_SHA=$(resolve_remote_sha "$GIT_URL" "$GIT_REF")
                if [[ -z "$REMOTE_SHA" ]]; then
                    echo "WARNING: could not reach $GIT_URL to check for updates (network?) — using existing checkout as-is"
                elif [[ "$REMOTE_SHA" == "$LOCAL_SHA" ]]; then
                    echo "Up to date at $LOCAL_SHA (matches $GIT_REF) — skipping clone/pip/npm"
                    [[ "$NO_BASELINE" == true ]] && echo "$LOCAL_SHA" >"$SYNC_STATE_FILE"
                else
                    echo "Remote $GIT_REF moved $LOCAL_SHA -> $REMOTE_SHA — fast-forwarding"
                    if git -C "$SIBLING_DIR" fetch --depth 1 "$GIT_URL" "$GIT_REF" 2>&1 &&
                        git -C "$SIBLING_DIR" reset --hard FETCH_HEAD 2>&1; then
                        NEEDS_PIP=true
                        git -C "$SIBLING_DIR" rev-parse HEAD >"$SYNC_STATE_FILE"
                    else
                        echo "WARNING: fast-forward failed for $NAME — using existing checkout as-is"
                    fi
                fi
            else
                # Clean, but local HEAD has moved past our recorded
                # baseline — a commit was made locally since we last
                # touched this checkout. Never auto-reset over it. If it
                # turns out local already matches the remote tip exactly
                # (e.g. that local commit was since pushed), re-arm the
                # baseline — that's pure bookkeeping, never a working-tree
                # mutation, so it's always safe.
                echo "Local HEAD ($LOCAL_SHA) differs from last-synced baseline — a local commit may be present; leaving checkout untouched"
                REMOTE_SHA=$(resolve_remote_sha "$GIT_URL" "$GIT_REF")
                if [[ -n "$REMOTE_SHA" ]] && [[ "$REMOTE_SHA" == "$LOCAL_SHA" ]]; then
                    echo "Local HEAD already matches $GIT_REF tip — re-arming auto-sync baseline"
                    echo "$LOCAL_SHA" >"$SYNC_STATE_FILE"
                fi
            fi
        fi
    fi

    # Validate manifest exists (cheap, always check)
    MANIFEST="$SIBLING_DIR/src/$PKG_NAME/_django/manifest.json"
    if [[ ! -f "$MANIFEST" ]]; then
        # Try repo root manifest
        MANIFEST="$SIBLING_DIR/manifest.json"
    fi
    if [[ -f "$MANIFEST" ]]; then
        echo "Manifest: $MANIFEST"
    else
        echo "WARNING: No manifest.json found for $NAME (no bridge)"
    fi

    # pip install — only when something changed above OR the package
    # doesn't already resolve to THIS exact checkout. The latter check is
    # what catches a fresh image rebuild: /app/.apps (and its git state)
    # persists across rebuilds, but site-packages is baked into the image
    # and resets to the Dockerfile-pinned PyPI version every time.
    if [[ -n "$PIP_PKG" ]]; then
        if [[ ! -d "$SIBLING_DIR" ]]; then
            echo "WARNING: $SIBLING_DIR not available — skipping pip install for $NAME"
        else
            ALREADY_SATISFIED=false
            if [[ "$NEEDS_PIP" != true ]]; then
                RESOLVED_SIBLING="$(cd "$SIBLING_DIR" && pwd)"
                CURRENT_LOCATION=$(python3 -c "
import importlib.util
spec = importlib.util.find_spec('${PKG_NAME}')
if spec and spec.submodule_search_locations:
    print(list(spec.submodule_search_locations)[0])
elif spec and spec.origin:
    print(spec.origin)
" 2>/dev/null || echo "")
                if [[ -n "$CURRENT_LOCATION" ]] && [[ "$CURRENT_LOCATION" == "$RESOLVED_SIBLING"* ]]; then
                    ALREADY_SATISFIED=true
                fi
            fi

            if [[ "$ALREADY_SATISFIED" == true ]]; then
                echo "$PIP_PKG already installed in editable mode from $SIBLING_DIR — skipping pip install"
            else
                # uv is the fast path (Docker/NAS: Dockerfile.prod installs
                # it explicitly, system site-packages is chowned to scitex
                # in root-init.sh specifically so --system can create/
                # replace package entries there). It is NOT guaranteed to
                # exist everywhere this script runs — e.g. GitHub-hosted CI
                # runners, which don't ship uv by default and this repo's
                # workflows don't install it. Silently no-op'ing there
                # (as an earlier version of this fix did) leaves the
                # PREVIOUSLY installed non-editable PyPI version resolvable
                # instead — vite.entries.ts's discoverPipEntries() has no
                # sibling-checkout fallback (unlike vite.config.ts's
                # discoverScitexUiStatic()) and just imports whatever
                # `scitex_ui` currently resolves to, so a stale wheel silently
                # becomes what gets bundled. Always fall back to plain pip
                # (always available wherever python is set up) so the
                # editable install genuinely happens either way; only the
                # SPEED differs, never correctness (2026-07-10, PR #331 CI
                # failure — pdfjs-dist unresolvable from the stale scitex-ui
                # 0.6.1 wheel because the editable install silently never
                # ran).
                PIP_INSTALL_OK=false
                if command -v uv &>/dev/null; then
                    echo "Installing: uv pip install -e $SIBLING_DIR"
                    # --system: see above (no venv in the Docker/NAS image).
                    # --break-system-packages: defensive only — the real
                    #   python:3.11-slim-bookworm runtime has no PEP 668
                    #   marker (unlike some OS-managed pythons), so this
                    #   should never actually trigger; costs nothing to pass.
                    # --link-mode=copy: site-packages and the uv cache volume
                    #   are on different mounts, so hardlinks aren't possible
                    #   anyway — avoid uv probing/falling back at every call.
                    if uv pip install --system --break-system-packages \
                        -e "$SIBLING_DIR" --link-mode=copy -q; then
                        PIP_INSTALL_OK=true
                    else
                        echo "WARNING: uv pip install failed for $NAME — falling back to plain pip"
                    fi
                else
                    echo "uv not found — using plain pip for $NAME"
                fi
                if [[ "$PIP_INSTALL_OK" != true ]]; then
                    # python3 -m pip (not bare `pip`): guarantees the install
                    # targets the SAME interpreter the find_spec gates above
                    # query, so the artifact check and the installer can never
                    # disagree about which environment they're talking about.
                    echo "Installing: python3 -m pip install -e $SIBLING_DIR"
                    if ! python3 -m pip install -e "$SIBLING_DIR" -q; then
                        # LOUD, fatal — no-silent-fallback. If the editable
                        # install cannot happen at all, whatever non-editable
                        # ${PKG_NAME} is already installed (e.g. the PyPI wheel
                        # pinned in Dockerfile.prod, or CI's own pip step)
                        # would silently become what vite bundles — exactly the
                        # confusing at-a-distance failure PR #331's first CI
                        # run produced. Fail here, at the true cause. Boot
                        # resilience is unchanged: entrypoint-prod.sh wraps
                        # this script in `|| echo_warning`, so a container
                        # still boots (with a visible warning); CI fails the
                        # step immediately.
                        echo "ERROR: editable install failed for $NAME (uv and pip both failed/unavailable)." >&2
                        echo "ERROR: refusing to continue silently — a stale non-editable ${PKG_NAME} would be used instead." >&2
                        exit 1
                    fi
                fi
            fi
        fi
    fi

    # npm install — mtime-gated per package.json found (root or nested
    # frontend dirs), mirroring the existing app-root npm-install idiom
    # in entrypoint-prod.sh ([ ! -d node_modules ] ||
    # [ package.json -nt node_modules/.install-timestamp ]).
    while IFS= read -r pkg_json; do
        pkg_dir="$(dirname "$pkg_json")"
        if [[ ! -d "$pkg_dir/node_modules" ]] || [[ "$pkg_json" -nt "$pkg_dir/node_modules/.install-timestamp" ]]; then
            echo "Running: npm install in $pkg_dir"
            (cd "$pkg_dir" && npm install --silent 2>/dev/null && touch node_modules/.install-timestamp) || true
        else
            echo "npm deps already up to date in $pkg_dir — skipping"
        fi
    done < <(find "$SIBLING_DIR" -maxdepth 5 -name "package.json" -not -path "*/node_modules/*" 2>/dev/null)

    echo "$NAME: OK"
done

echo ""
echo "All apps installed. Vite can now resolve bridge entries."
