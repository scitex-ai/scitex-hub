#!/usr/bin/env bash
# Start a throwaway Gitea for tests that need a REAL repository server.
#
# Project creation is Gitea-first: the post_save signal creates the repository,
# clones it, and the template step publishes into it. A test of "create a
# project from every offered template" therefore needs a live Gitea, or it is
# a test of something else. The main pytest job deliberately runs without one
# (see pytest-matrix workflow), so this script gives the dedicated job, and a
# developer's machine, the same disposable server: a pinned, checksum-verified
# Gitea binary on 127.0.0.1 with sqlite, an admin user and an API token.
#
# Usage: start_test_gitea.sh <work-dir> [port]
#   Writes <work-dir>/env with the variables Django's dev settings read
#   (SCITEX_HUB_GITEA_URL_IN_CONTAINER_DEV, SCITEX_HUB_GITEA_TOKEN_DEV) and
#   <work-dir>/gitea.pid. Stop with: kill "$(cat <work-dir>/gitea.pid)".
set -euo pipefail

GITEA_VERSION="1.22.6"
GITEA_SHA256="fd77f1a0273c85a0950207c1cfa6753a9fa57604e4ab1382484b191cc919ce15"

work_dir="${1:?usage: start_test_gitea.sh <work-dir> [port]}"
port="${2:-3999}"
mkdir -p "$work_dir"
work_dir="$(cd "$work_dir" && pwd)"

binary="$work_dir/gitea-$GITEA_VERSION"
if [ ! -x "$binary" ]; then
    curl -fsSL --retry 3 -o "$binary.part" \
        "https://dl.gitea.com/gitea/$GITEA_VERSION/gitea-$GITEA_VERSION-linux-amd64"
    echo "$GITEA_SHA256  $binary.part" | sha256sum -c - >/dev/null
    chmod +x "$binary.part"
    mv "$binary.part" "$binary"
fi

config="$work_dir/app.ini"
cat >"$config" <<EOF
APP_NAME = hub-test-gitea
RUN_MODE = prod
WORK_PATH = $work_dir

[server]
HTTP_ADDR = 127.0.0.1
HTTP_PORT = $port
ROOT_URL = http://127.0.0.1:$port/
DISABLE_SSH = true
OFFLINE_MODE = true

[database]
DB_TYPE = sqlite3
PATH = $work_dir/gitea.db

[repository]
ROOT = $work_dir/repositories
DEFAULT_BRANCH = main

[security]
INSTALL_LOCK = true
SECRET_KEY = hub-test-gitea-not-a-secret

[service]
DISABLE_REGISTRATION = true

[log]
MODE = file
ROOT_PATH = $work_dir/log
LEVEL = Warn
EOF

# Gitea runs git for every repository it creates (auto-init pushes through
# the repository's server hooks). A developer's own git configuration --
# global hooks, templates, includes -- must not leak into that, so the server
# gets a clean environment with its own empty HOME.
mkdir -p "$work_dir/home"
gitea() {
    env -i HOME="$work_dir/home" PATH="/usr/local/bin:/usr/bin:/bin" \
        GIT_CONFIG_NOSYSTEM=1 \
        "$binary" --config "$config" --work-path "$work_dir" "$@"
}

gitea migrate >/dev/null
gitea admin user create \
    --admin --username hubtestadmin --email hubtestadmin@example.invalid \
    --password "hub-test-admin-$(date +%s)" --must-change-password=false \
    >/dev/null 2>&1 || true  # already present on a re-run

# Not through gitea(): $! must be the server's pid (env execs the binary).
env -i HOME="$work_dir/home" PATH="/usr/local/bin:/usr/bin:/bin" \
    GIT_CONFIG_NOSYSTEM=1 \
    "$binary" --config "$config" --work-path "$work_dir" web \
    >"$work_dir/web.log" 2>&1 </dev/null &
echo $! >"$work_dir/gitea.pid"

for _ in $(seq 1 60); do
    if curl -fsS "http://127.0.0.1:$port/api/healthz" >/dev/null 2>&1; then
        break
    fi
    sleep 1
done
curl -fsS "http://127.0.0.1:$port/api/healthz" >/dev/null

token="$(gitea admin user generate-access-token --username hubtestadmin \
    --token-name "hub-test-$(date +%s%N)" --scopes all --raw)"

# The organisation hub publishes app scaffolds into (APPS_ORG in
# apps/workspace/apps_app/views/api_registry.py); every deployment has it.
status="$(curl -sS -o /dev/null -w '%{http_code}' -X POST \
    -H "Authorization: token $token" -H 'Content-Type: application/json' \
    -d '{"username": "scitex-apps", "visibility": "public"}' \
    "http://127.0.0.1:$port/api/v1/orgs")"
case "$status" in 201 | 422) ;; *) echo "creating org scitex-apps: HTTP $status" >&2; exit 1 ;; esac

umask 077
cat >"$work_dir/env" <<EOF
SCITEX_HUB_GITEA_URL_IN_CONTAINER_DEV=http://127.0.0.1:$port
SCITEX_HUB_GITEA_URL_DEV=http://127.0.0.1:$port
SCITEX_HUB_GITEA_TOKEN_DEV=$token
EOF
echo "Gitea $GITEA_VERSION ready on http://127.0.0.1:$port (env: $work_dir/env)"
