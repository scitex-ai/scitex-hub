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
#   VENV       python venv to create              (default: ~/.venv-hub)
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
# 4. DOCKER + NODE ALONE LEAVE THE HOST UNABLE TO BUILD. scripts/apps/install_apps.sh
#    installs the sibling apps editable; `uv pip install --system` fails with
#    Permission denied on /usr/local/lib/python3.12/dist-packages for a non-root
#    user, and plain pip fails with externally-managed-environment (PEP 668).
#    The script then correctly REFUSES to continue rather than leave a stale
#    non-editable scitex_ui behind, so the build never starts. A writable python
#    env is a real prerequisite, not a nicety — this is exactly where the first
#    version of this script stopped, and the host looked provisioned but was not.
# 5. `command -v python3 -m pip` DOES NOT TEST PIP — it is a gate that cannot
#    fail. `command -v` takes command NAMES and ignores trailing arguments, so
#    it reports on `python3` alone and returns 0 on every box that ships python3
#    (i.e. all of them). Proven with a control: `command -v python3 -m
#    NONEXISTENT_MODULE` also returns 0. The apt step it guarded was therefore
#    skipped on a host with neither python3-pip nor python3-venv, and step 5
#    then died on `python3 -m venv`. It survived review because scitex-01
#    happened to have pip 24.0 preinstalled, so the guard was never exercised.
#    Test a MODULE by importing/running it, never by naming it to `command -v`.
#    Note `python3 -m venv --help` is the same non-gate: the venv module is in
#    the stdlib while ensurepip — the part venv actually needs to create an env
#    — is split into the python3-venv package on Debian/Ubuntu. Import ensurepip.
set -uo pipefail

DATA_VOL="${DATA_VOL:-/scratch}"
# `id -un` last, not $USER: with `set -u` an unset USER aborts the whole script
# on this line, before a single check runs. USER is unset in plenty of the
# contexts this is meant for (cron, systemd, `docker exec`, some ssh setups).
NODE_USER="${NODE_USER:-${SUDO_USER:-${USER:-$(id -un)}}}"
NODE_MAJOR="${NODE_MAJOR:-20}"
VENV="${VENV:-$HOME/.venv-hub}"
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

    # Python side. scripts/apps/install_apps.sh needs a WRITABLE python env or
    # it refuses to run — see TRAP 4.
    command -v uv >/dev/null && ok "uv $(uv --version 2>/dev/null | awk '{print $2}')" \
        || bad "uv missing (install_apps.sh prefers it)"
    [ -x "${VENV}/bin/python" ] && ok "venv at ${VENV}" || bad "no venv at ${VENV}"
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

echo "== 5. python tooling + venv =="
# WHY A VENV IS NOT OPTIONAL (TRAP 4): scripts/apps/install_apps.sh installs the
# sibling apps editable. It tries `uv pip install --system` first, which on a
# non-root user fails with "Permission denied" on
# /usr/local/lib/python3.12/dist-packages, then falls back to plain pip, which
# on Ubuntu 24.04 fails with "externally-managed-environment" (PEP 668). With
# neither available the script correctly REFUSES to continue rather than leave a
# stale non-editable scitex_ui behind — so the build never starts. A writable
# env is the actual prerequisite, and provisioning that stops at docker+node
# leaves the host unable to build anything.
# TRAP 5: test the MODULES by running them. `command -v python3 -m pip` returns
# 0 whenever python3 exists, so it never once forced this install.
NEED_PKGS=""
python3 -m pip --version   >/dev/null 2>&1 || NEED_PKGS="${NEED_PKGS} python3-pip"
python3 -c 'import ensurepip' >/dev/null 2>&1 || NEED_PKGS="${NEED_PKGS} python3-venv"
if [ -n "$NEED_PKGS" ]; then
    echo "  installing:${NEED_PKGS}"
    s env DEBIAN_FRONTEND=noninteractive apt-get update -qq
    s env DEBIAN_FRONTEND=noninteractive apt-get install -y -qq $NEED_PKGS
else
    echo "  python3-pip and python3-venv already present"
fi
if command -v uv >/dev/null; then
    echo "  uv already present"
else
    # To a file, then run — never pipe a vendor installer straight into a shell.
    curl -fsSL https://astral.sh/uv/install.sh -o /tmp/uv.$$.sh && sh /tmp/uv.$$.sh >/dev/null 2>&1
    rm -f /tmp/uv.$$.sh
fi
export PATH="$HOME/.local/bin:$PATH"
if [ ! -d "$VENV" ]; then
    # Say WHAT to do, not just what broke: the failure here is almost always the
    # ensurepip split, and the package name is interpreter-versioned on Ubuntu.
    if ! python3 -m venv "$VENV"; then
        printf '  \033[0;31mFAIL\033[0m could not create venv at %s\n' "$VENV" >&2
        echo "        most likely ensurepip is missing (Debian/Ubuntu splits it out)" >&2
        echo "        fix: sudo apt-get install -y python3-venv" >&2
        echo "             or the versioned name, e.g. python3.12-venv" >&2
        echo "        then re-run this script; verify with --check" >&2
        RC=1
    fi
fi
echo "  venv: ${VENV}"

echo "== 6. restart docker so daemon.json takes effect =="
s systemctl enable --now docker >/dev/null 2>&1
s systemctl restart docker >/dev/null 2>&1
sleep 4

check
rc=$?
cat <<EOF

NEXT (not done here — needs the repo checked out):
  source ${VENV}/bin/activate
  cd <repo> && bash scripts/apps/install_apps.sh && npm install && npx vite build
Order matters: install_apps.sh BEFORE npm install, because package.json
references file:../scitex-ui and file:../figrecipe/... as siblings.
EOF
exit $rc
