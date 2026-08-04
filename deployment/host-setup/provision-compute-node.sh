#!/bin/bash
# Timestamp: "2026-08-05"
# File: deployment/host-setup/provision-compute-node.sh
#
# PURPOSE
# -------
# Turn a bare Ubuntu box into a SciTeX build/test node, reproducibly.
# Written while provisioning scitex-01 (Ryzen 9 5950X, 32T, 62 GB) so that
# scitex-02 and every node after it is one command instead of an afternoon.
#
# WHY THIS EXISTS RATHER THAN A WIKI PAGE: the first run of this by hand hit
# three traps that a prose checklist would not have caught (see TRAPS below).
# Each is encoded here as a step plus a check that can actually fail.
#
# USAGE
# -----
#   ./provision-compute-node.sh --check          # verify only, changes nothing
#   ./provision-compute-node.sh                  # provision (asks for sudo)
#
#   # remote, password piped on STDIN (never on argv — /proc/<pid>/cmdline is
#   # world-readable, environ is not):
#   gpg -d ~/.pw/<node>-sudo.gpg | ssh <node> 'bash -s -- --stdin-pw' \
#       < provision-compute-node.sh
#
# TUNABLES (env)
# --------------
#   DATA_VOL   volume for docker's data-root      (default: /scratch)
#   NODE_USER  user to add to the docker group    (default: $SUDO_USER or $USER)
#   NODE_MAJOR node major version to install      (default: 20 — MUST match CI)
#
# TRAPS THIS ENCODES — each cost real time on scitex-01, 2026-08-04
# -----------------------------------------------------------------
# 1. `printf '{...}' | sudo -S tee /etc/docker/daemon.json` WRITES NOTHING.
#    A `sudo -S` helper that pipes the password in owns stdin, so the payload
#    is replaced by the password; sudo eats the first line to authenticate and
#    tee gets EOF. Result: a 0-byte config that LOOKS written. Stage to a temp
#    file as the user and `sudo cp` it instead — done below.
#    (Also verify the secret did not land in the file: had sudo not consumed
#    that line, tee would have written the PASSWORD to a root-owned path.)
# 2. daemon.json alone proves nothing. Docker must be RESTARTED, and the check
#    must read `docker info --format '{{.DockerRootDir}}'` from the RUNNING
#    daemon. Writing the file and declaring success leaves images on the small
#    root volume, discovered weeks later as a disk-full with no obvious cause.
# 3. Ubuntu 24.04 ships node 18.19; CI pins node 20 in every workflow. A node
#    that does not match CI makes every local build result meaningless — a
#    failure here must mean something about the code, not about version skew.
set -uo pipefail

DATA_VOL="${DATA_VOL:-/scratch}"
NODE_USER="${NODE_USER:-${SUDO_USER:-$USER}}"
NODE_MAJOR="${NODE_MAJOR:-20}"
DOCKER_ROOT="${DATA_VOL}/docker"
MODE="${1:-}"

PW=""
if [ "$MODE" = "--stdin-pw" ]; then read -rs PW; MODE="${2:-}"; fi
s() { if [ -n "$PW" ]; then printf '%s\n' "$PW" | sudo -S -p '' "$@"; else sudo "$@"; fi; }

ok() { printf '  \033[0;32mPASS\033[0m %s\n' "$1"; }
bad() { printf '  \033[0;31mFAIL\033[0m %s\n' "$1"; RC=1; }
RC=0

check() {
    echo "== verifying =="
    command -v docker >/dev/null && ok "docker $(docker --version | awk '{print $3}' | tr -d ,)" \
        || bad "docker missing"
    docker compose version >/dev/null 2>&1 && ok "compose $(docker compose version --short 2>/dev/null)" \
        || bad "docker compose plugin missing"
    command -v make >/dev/null && ok "make $(make --version | head -1 | awk '{print $3}')" || bad "make missing"

    local nv; nv="$(node --version 2>/dev/null)"
    case "$nv" in
        v${NODE_MAJOR}.*) ok "node $nv (matches CI major ${NODE_MAJOR})";;
        "") bad "node missing (CI uses ${NODE_MAJOR})";;
        *) bad "node $nv does NOT match CI major ${NODE_MAJOR} — local results would be meaningless";;
    esac

    # THE check that matters: what the RUNNING daemon uses, not what a file says.
    local root; root="$(s docker info --format '{{.DockerRootDir}}' 2>/dev/null)"
    case "$root" in
        "${DOCKER_ROOT}"*) ok "docker data-root is ${root}";;
        "") bad "could not read DockerRootDir (daemon down?)";;
        *) bad "docker data-root is ${root}, expected ${DOCKER_ROOT} — images will fill the small volume";;
    esac

    id -nG "$NODE_USER" 2>/dev/null | tr ' ' '\n' | grep -qx docker \
        && ok "${NODE_USER} in docker group" || bad "${NODE_USER} not in docker group"
    return $RC
}

if [ "$MODE" = "--check" ]; then check; exit $?; fi

echo "== 1. docker data-root on ${DATA_VOL} (BEFORE first pull) =="
if [ ! -d "$DATA_VOL" ]; then
    echo "  ${DATA_VOL} does not exist — falling back to the docker default"
else
    s mkdir -p "$DOCKER_ROOT" /etc/docker
    # Stage as the user, then copy. See TRAP 1.
    printf '{\n  "data-root": "%s"\n}\n' "$DOCKER_ROOT" > /tmp/daemon.json.$$
    s cp /tmp/daemon.json.$$ /etc/docker/daemon.json
    s chmod 644 /etc/docker/daemon.json
    rm -f /tmp/daemon.json.$$
    echo "  wrote /etc/docker/daemon.json -> ${DOCKER_ROOT}"
fi

echo "== 2. docker, compose, make =="
if command -v docker >/dev/null; then
    echo "  docker already present"
else
    s env DEBIAN_FRONTEND=noninteractive apt-get update -qq
    s env DEBIAN_FRONTEND=noninteractive apt-get install -y -qq docker.io docker-compose-v2 make
fi

echo "== 3. node ${NODE_MAJOR} (must match CI) =="
if node --version 2>/dev/null | grep -q "^v${NODE_MAJOR}\."; then
    echo "  node $(node --version) already present"
else
    # To a FILE, then run. Piping a vendor script straight into sudo hides what ran.
    curl -fsSL "https://deb.nodesource.com/setup_${NODE_MAJOR}.x" -o /tmp/nodesource.$$.sh
    s bash /tmp/nodesource.$$.sh >/dev/null 2>&1
    s env DEBIAN_FRONTEND=noninteractive apt-get install -y -qq nodejs
    rm -f /tmp/nodesource.$$.sh
fi

echo "== 4. docker group =="
id -nG "$NODE_USER" | tr ' ' '\n' | grep -qx docker \
    && echo "  ${NODE_USER} already in docker group" \
    || { s usermod -aG docker "$NODE_USER"; echo "  added ${NODE_USER} (effective next login)"; }

echo "== 5. restart docker so daemon.json takes effect =="
s systemctl enable --now docker >/dev/null 2>&1
s systemctl restart docker >/dev/null 2>&1
sleep 4

check
exit $?
