#!/bin/bash
# Kept for existing runbooks: the slurmctld drop-in is now installed together with
# the drop-ins for mariadb, munge, slurmdbd and slurmd. See install-slurm-resilience.sh.
#
# Usage: sudo ./install-slurmctld-resilience.sh

exec "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/install-slurm-resilience.sh" "$@"
