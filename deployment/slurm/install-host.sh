#!/bin/bash
# =============================================================================
# SLURM Host Installation for SciTeX Hub
# =============================================================================
# Builds SLURM 24.05.5 from source to match Docker container version.
# Usage: sudo ./install-host.sh
# Build time: ~10 minutes
# =============================================================================

set -e

SLURM_VERSION="24.05.5"
BUILD_DIR="/tmp/slurm-build"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Auto-detect hardware
NODE_NAME="$(hostname -s)"
NODE_CPUS="$(nproc)"
NODE_MEMORY="$(free -m | awk '/^Mem:/{print int($2 * 0.9)}')"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

log()  { echo -e "${GREEN}[+]${NC} $1"; }
warn() { echo -e "${YELLOW}[!]${NC} $1"; }
err()  { echo -e "${RED}[ERROR]${NC} $1"; exit 1; }

[[ $EUID -ne 0 ]] && err "Run with: sudo $0"

echo -e "=============================================="
echo -e " SLURM ${SLURM_VERSION} Installation"
echo -e "=============================================="
echo -e ""
echo -e " Node:     $NODE_NAME"
echo -e " CPUs:     $NODE_CPUS"
echo -e " Memory:   ${NODE_MEMORY} MB"
echo -e " Build:    ~10 minutes"
echo -e ""

# =============================================================================
# Step 1: Remove old SLURM
# =============================================================================
log "Removing old SLURM packages..."
systemctl stop slurmctld slurmd 2>/dev/null || true
pkill -9 slurmctld slurmd slurmstepd 2>/dev/null || true

apt-get remove -y slurm-wlm slurm-client slurmctld slurmd slurm-wlm-basic-plugins 2>/dev/null || true
apt-get remove -y slurm-smd slurm-smd-client slurm-smd-slurmctld slurm-smd-slurmd 2>/dev/null || true
apt-get autoremove -y 2>/dev/null || true

# =============================================================================
# Step 2: Install build dependencies
# =============================================================================
log "Installing build dependencies..."
apt-get update -qq
apt-get install -y -qq \
    build-essential fakeroot devscripts equivs \
    libmunge-dev libmunge2 munge \
    libmariadb-dev libpam0g-dev libssl-dev \
    libjson-c-dev libhttp-parser-dev libcurl4-openssl-dev \
    liblz4-dev libyaml-dev libjwt-dev libdbus-1-dev \
    libsystemd-dev liblua5.4-dev man2html-base curl

# =============================================================================
# Step 3: Download and build SLURM
# =============================================================================
log "Downloading SLURM ${SLURM_VERSION}..."
mkdir -p "$BUILD_DIR"
cd "$BUILD_DIR"

if [[ ! -f "slurm-${SLURM_VERSION}.tar.bz2" ]]; then
    curl -sL -o "slurm-${SLURM_VERSION}.tar.bz2" \
        "https://download.schedmd.com/slurm/slurm-${SLURM_VERSION}.tar.bz2"
fi

log "Building SLURM (this takes ~10 minutes)..."
rm -rf "slurm-${SLURM_VERSION}"
tar -xf "slurm-${SLURM_VERSION}.tar.bz2"
cd "slurm-${SLURM_VERSION}"

mk-build-deps --install --tool='apt-get -o Debug::pkgProblemResolver=yes --no-install-recommends --yes' debian/control 2>/dev/null || true
debuild -b -uc -us -j$(nproc) 2>&1 | tail -10

# =============================================================================
# Step 4: Install packages
# =============================================================================
log "Installing SLURM packages..."
cd "$BUILD_DIR"
dpkg -i slurm-smd_${SLURM_VERSION}*.deb \
        slurm-smd-client_${SLURM_VERSION}*.deb \
        slurm-smd-slurmctld_${SLURM_VERSION}*.deb \
        slurm-smd-slurmd_${SLURM_VERSION}*.deb 2>/dev/null || true
apt-get install -f -y -qq

# =============================================================================
# Step 5: Configure MUNGE
# =============================================================================
log "Configuring MUNGE..."
if [[ ! -f /etc/munge/munge.key ]]; then
    create-munge-key -f 2>/dev/null || dd if=/dev/urandom bs=1 count=1024 of=/etc/munge/munge.key 2>/dev/null
fi
chown -R munge:munge /etc/munge /var/log/munge /var/lib/munge /run/munge 2>/dev/null || true
chmod 0700 /etc/munge
chmod 0400 /etc/munge/munge.key
systemctl enable munge
systemctl restart munge
sleep 1
munge -n | unmunge > /dev/null && log "MUNGE OK" || err "MUNGE failed"

# =============================================================================
# Step 6: Create directories
# =============================================================================
log "Creating directories..."
mkdir -p /etc/slurm /var/log/slurm /var/spool/slurmctld /var/spool/slurmd /run/slurmctld /run/slurmd

# Create slurm user if needed
id slurm &>/dev/null || useradd -r -s /bin/false slurm

chown -R slurm:slurm /var/log/slurm /var/spool/slurmctld /var/spool/slurmd /run/slurmctld /run/slurmd
chmod 755 /var/log/slurm /var/spool/slurmctld /var/spool/slurmd /run/slurmctld /run/slurmd

cat > /etc/tmpfiles.d/slurm.conf << 'EOF'
d /run/slurmctld 0755 slurm slurm -
d /run/slurmd 0755 slurm slurm -
EOF
systemd-tmpfiles --create 2>/dev/null || true

# =============================================================================
# Step 7: Generate config
# =============================================================================
log "Generating SLURM configuration..."

cat > /etc/slurm/slurm.conf << EOF
# SLURM Configuration for SciTeX Hub
# Generated: $(date)

ClusterName=scitex
SlurmctldHost=${NODE_NAME}
SlurmUser=slurm

NodeName=${NODE_NAME} CPUs=${NODE_CPUS} RealMemory=${NODE_MEMORY} State=UNKNOWN

PartitionName=normal  Nodes=${NODE_NAME} Default=YES MaxTime=24:00:00 State=UP
PartitionName=express Nodes=${NODE_NAME} MaxTime=04:00:00 State=UP Priority=100
PartitionName=long    Nodes=${NODE_NAME} MaxTime=7-00:00:00 State=UP

SchedulerType=sched/backfill
SelectType=select/cons_tres
SelectTypeParameters=CR_Core_Memory

ProctrackType=proctrack/linuxproc
TaskPlugin=task/none

StateSaveLocation=/var/spool/slurmctld
SlurmdSpoolDir=/var/spool/slurmd
SlurmctldPidFile=/run/slurmctld/slurmctld.pid
SlurmdPidFile=/run/slurmd/slurmd.pid

SlurmctldLogFile=/var/log/slurm/slurmctld.log
SlurmdLogFile=/var/log/slurm/slurmd.log
SlurmctldDebug=info
SlurmdDebug=info

SlurmctldTimeout=300
SlurmdTimeout=300
ReturnToService=2

AccountingStorageType=accounting_storage/none
JobAcctGatherType=jobacct_gather/none
EOF

chown slurm:slurm /etc/slurm/slurm.conf
chmod 644 /etc/slurm/slurm.conf

# Generate Docker config
log "Generating Docker client config..."
sed "s/SlurmctldHost=${NODE_NAME}/SlurmctldHost=host.docker.internal/" \
    /etc/slurm/slurm.conf > "${SCRIPT_DIR}/slurm-docker.conf"
chmod 644 "${SCRIPT_DIR}/slurm-docker.conf"

# =============================================================================
# Step 8: Start services
# =============================================================================
log "Starting SLURM services..."

# Clear old state
rm -rf /var/spool/slurmctld/* /var/spool/slurmd/*

systemctl unmask slurmctld slurmd 2>/dev/null || true
systemctl daemon-reload
systemctl enable slurmctld slurmd
systemctl restart slurmctld
sleep 3
systemctl restart slurmd
sleep 2

scontrol update nodename=${NODE_NAME} state=idle 2>/dev/null || true

# =============================================================================
# Verify
# =============================================================================
echo -e ""
log "Verifying..."
sinfo --version
echo -e ""
sinfo

echo -e ""
if srun --partition=express hostname 2>/dev/null; then
    echo -e "${GREEN}=============================================="
    echo -e " SLURM ${SLURM_VERSION} Installation Complete!"
    echo -e "==============================================${NC}"
else
    warn "srun test failed. Run: sudo ./fix.sh"
fi
