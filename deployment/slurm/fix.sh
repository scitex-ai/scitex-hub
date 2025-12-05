#!/bin/bash
# SLURM Fix Script - Run when things break
# Usage: sudo ./fix.sh

[[ $EUID -ne 0 ]] && { echo -e "Run with sudo"; exit 1; }

NODE=$(hostname -s)

echo -e "Fixing SLURM..."

# Stop and kill everything
systemctl stop slurmctld slurmd 2>/dev/null
pkill -9 slurmctld slurmd slurmstepd 2>/dev/null

# Clear state
rm -rf /var/spool/slurmctld/* /var/spool/slurmd/*

# Fix munge
systemctl restart munge
sleep 1

# Start services
systemctl start slurmctld
sleep 2
systemctl start slurmd
sleep 2

# Set node idle
scontrol update nodename=$NODE state=idle 2>/dev/null

# Verify
echo -e ""
sinfo
echo -e ""
if srun --partition=express hostname 2>/dev/null; then
    echo -e "SLURM OK"
else
    echo -e "Still broken. Check: journalctl -u slurmd -n 20"
fi
