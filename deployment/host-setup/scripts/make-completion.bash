#!/bin/bash
# ---
# Timestamp: 2026-03-21
# File: deployment/host-setup/scripts/make-completion.bash
# ---
# Tab completion for scitex-cloud Makefile.
# Completes target names and ENV= values.
#
# Installation (add to ~/.bashrc):
#   source /path/to/scitex-cloud/deployment/host-setup/scripts/make-completion.bash
#
# Or install via: make install-completion

_scitex_make_completion() {
    local cur prev targets envs
    COMPREPLY=()
    cur="${COMP_WORDS[COMP_CWORD]}"
    prev="${COMP_WORDS[COMP_CWORD-1]}"

    # Available environments
    envs="dev staging prod"

    # Complete ENV= or env=
    if [[ "$cur" == ENV=* ]] || [[ "$cur" == env=* ]]; then
        local prefix="${cur%%=*}="
        local typed="${cur#*=}"
        COMPREPLY=($(compgen -W "${envs}" -- "$typed"))
        COMPREPLY=("${COMPREPLY[@]/#/${prefix}}")
        return 0
    fi

    # Extract targets from Makefile in current or project directory
    local makefile=""
    if [ -f "Makefile" ]; then
        makefile="Makefile"
    elif [ -f "${SCITEX_HUB_ROOT:-}/Makefile" ]; then
        makefile="${SCITEX_HUB_ROOT}/Makefile"
    fi

    if [ -n "$makefile" ]; then
        targets=$(grep -oE '^[a-zA-Z_-]+:' "$makefile" | sed 's/://' | sort -u)
    fi

    # Add env= as a completable prefix
    COMPREPLY=($(compgen -W "${targets} env= ENV=" -- "$cur"))
    return 0
}

complete -o nospace -F _scitex_make_completion make
