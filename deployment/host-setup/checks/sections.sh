#!/bin/bash
# The status section registry — the ONE list of what a status check covers.
#
# WHY THIS FILE EXISTS
# --------------------
# There were two lists. `make status` (check-status.sh) ran fifteen numbered
# sections; `make status-live` (scripts/maintenance/check_status_live.sh)
# hand-inlined its own bash for five of them. Adding a check meant editing both,
# and nobody did: ten sections existed only in `status`, DISK AMONG THEM. On
# 2026-08-09 a 393G volume filled to 100% with nothing alarming, and one of the
# two commands an admin might run to look was structurally unable to notice.
#
# So the list is data, in one place, and both orchestrators iterate it. A new
# check is one line HERE and appears in both surfaces at once. Neither script
# names a section anywhere else — tests/config/test_status_sections_single_source.py
# fails if either grows a second list.
#
# CONTRACT
# --------
# `status_sections` prints one section per line as: <name><TAB><command>
#   name     stable ordering key, also the temp-file name in the parallel run.
#   command  an executable path. EVERY section is a script, with no inline
#            special cases — that uniformity is what lets a second orchestrator
#            consume this list without importing the first one's functions.
#
# Callers must set SECTIONS_SCRIPT_DIR (this directory) and SECTIONS_PROJECT_ROOT
# before sourcing, so this file resolves paths without assuming where it was
# sourced from.

set -uo pipefail

status_sections() {
    local d="${SECTIONS_SCRIPT_DIR:?SECTIONS_SCRIPT_DIR must be set before sourcing sections.sh}"
    local r="${SECTIONS_PROJECT_ROOT:?SECTIONS_PROJECT_ROOT must be set before sourcing sections.sh}"

    printf '%s\t%s\n' \
        "01-env"        "${d}/check-environment.sh" \
        "02-docker"     "${d}/check-docker.sh" \
        "03-migrations" "${d}/check-migrations.sh" \
        "03b-db-modules" "${d}/check-db-modules.sh" \
        "04-visitors"   "${d}/check-visitor-pool.sh" \
        "05-slurm"      "${d}/check-slurm.sh" \
        "06-host"       "${d}/check-users.sh" \
        "07-terminal"   "${d}/check-terminal-ready.sh" \
        "08-filesizes"  "${r}/scripts/maintenance/check_file_sizes.sh" \
        "09-apptainer"  "${d}/check-apptainer.sh" \
        "10-services"   "${d}/check-services.sh" \
        "11-resources"  "${d}/check-resource-limits.sh" \
        "12-portfwd"    "${d}/check-port-forwarding.sh" \
        "13-app-drift"  "${d}/check-app-drift.sh" \
        "14-disk"       "${r}/scripts/maintenance/check_disk_space.sh"
}
