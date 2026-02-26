#!/bin/bash
# Timestamp: "2026-02-25"
# File: deployment/host-setup/install-packages.sh
#
# PURPOSE
# -------
# Install host-level packages that are bind-mounted into Apptainer/Docker
# containers at runtime, instead of baking them into container images.
# This avoids large image rebuilds when package versions change, and lets
# containers share a single authoritative installation from the host.
#
# USAGE
# -----
#   sudo ./install-packages.sh             # install everything (default)
#   sudo ./install-packages.sh --all       # same as above
#   sudo ./install-packages.sh --texlive   # texlive only
#   sudo ./install-packages.sh --imagemagick  # imagemagick only
#   sudo ./install-packages.sh --check     # verify without installing
#
# BIND-MOUNT EXAMPLE (Apptainer)
# --------------------------------
#   apptainer run \
#     --bind /usr/share/texmf:/usr/share/texmf:ro \
#     --bind /usr/bin/pdflatex:/usr/bin/pdflatex:ro \
#     myimage.sif
#
# ENV VAR GUIDANCE
# ----------------
# After install, set these in your .env or container launch script:
#   HOST_TEXLIVE_DIR=/usr/share/texlive
#   HOST_TEXMF_DIR=/usr/share/texmf
#   HOST_IMAGEMAGICK_POLICY=/etc/ImageMagick-6/policy.xml
#
# IDEMPOTENT: safe to re-run; already-installed packages are skipped by apt.

set -euo pipefail

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

SCRIPT_NAME="$(basename "${BASH_SOURCE[0]}")"
LOG_PREFIX="[install-packages]"

# TeXLive packages — mirrors what docker_prod/Dockerfile.prod installs
TEXLIVE_PACKAGES=(
    texlive-latex-base
    texlive-latex-extra
    texlive-latex-recommended
    texlive-fonts-recommended
    texlive-fonts-extra
    texlive-bibtex-extra
    texlive-science
    texlive-pictures
    texlive-plain-generic
    latexdiff
    latexmk
    ghostscript
    poppler-utils
)

# ImageMagick packages
IMAGEMAGICK_PACKAGES=(
    imagemagick
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

info() { echo "${LOG_PREFIX} INFO:  $*"; }
success() { echo "${LOG_PREFIX} OK:    $*"; }
warn() { echo "${LOG_PREFIX} WARN:  $*" >&2; }
error() {
    echo "${LOG_PREFIX} ERROR: $*" >&2
    exit 1
}

check_root() {
    if [[ "${EUID}" -ne 0 ]]; then
        error "This script must be run with sudo or as root."
    fi
}

apt_install() {
    local packages=("$@")
    info "Running: apt-get install -y --no-install-recommends ${packages[*]}"
    apt-get install -y --no-install-recommends "${packages[@]}"
}

# ---------------------------------------------------------------------------
# Install functions
# ---------------------------------------------------------------------------

install_texlive() {
    info "Updating apt cache..."
    apt-get update -qq

    info "Installing TeXLive packages..."
    apt_install "${TEXLIVE_PACKAGES[@]}"

    success "TeXLive packages installed."
}

fix_imagemagick_pdf_policy() {
    # ImageMagick ships with a restrictive security policy that blocks PDF
    # conversion. We patch it to allow read|write for PDF, matching what the
    # production Dockerfile does.
    local policy_file="/etc/ImageMagick-6/policy.xml"

    if [[ ! -f "${policy_file}" ]]; then
        warn "ImageMagick policy file not found at ${policy_file} — skipping PDF policy fix."
        return 0
    fi

    # Check if already patched (idempotent guard)
    if grep -q 'rights="read|write" pattern="PDF"' "${policy_file}"; then
        info "ImageMagick PDF policy already allows read|write — no change needed."
        return 0
    fi

    info "Patching ImageMagick policy.xml to allow PDF read|write..."
    sed -i \
        's|<policy domain="coder" rights="none" pattern="PDF" />|<policy domain="coder" rights="read|write" pattern="PDF" />|g' \
        "${policy_file}"

    if grep -q 'rights="read|write" pattern="PDF"' "${policy_file}"; then
        success "ImageMagick PDF policy patched."
    else
        warn "Patch command ran but expected pattern not found. Manual inspection may be needed: ${policy_file}"
    fi
}

install_imagemagick() {
    info "Updating apt cache..."
    apt-get update -qq

    info "Installing ImageMagick..."
    apt_install "${IMAGEMAGICK_PACKAGES[@]}"

    fix_imagemagick_pdf_policy
    success "ImageMagick installed."
}

# ---------------------------------------------------------------------------
# Verification
# ---------------------------------------------------------------------------

verify_tool() {
    local name="$1"
    local cmd="$2"

    if command -v "${cmd}" &>/dev/null; then
        local version
        version="$("${cmd}" --version 2>&1 | head -1)"
        success "${name}: ${version}"
        return 0
    else
        warn "${name}: NOT FOUND (command: ${cmd})"
        return 1
    fi
}

run_verification() {
    info "------------------------------------------------------------"
    info "Verifying installed tools..."
    info "------------------------------------------------------------"

    local failed=0

    verify_tool "pdflatex" "pdflatex" || ((failed++))
    verify_tool "bibtex" "bibtex" || ((failed++))
    verify_tool "latexmk" "latexmk" || ((failed++))
    verify_tool "latexdiff" "latexdiff" || ((failed++))
    verify_tool "ghostscript" "gs" || ((failed++))
    verify_tool "pdfinfo (poppler)" "pdfinfo" || ((failed++))
    verify_tool "convert (ImageMagick)" "convert" || ((failed++))

    info "------------------------------------------------------------"

    if [[ "${failed}" -eq 0 ]]; then
        success "All tools verified successfully."
        return 0
    else
        warn "${failed} tool(s) failed verification. See warnings above."
        return 1
    fi
}

# ---------------------------------------------------------------------------
# Env var guidance
# ---------------------------------------------------------------------------

print_env_guidance() {
    echo ""
    echo "=================================================================="
    echo " ENV VAR GUIDANCE"
    echo "=================================================================="
    echo " Add these to your .env or container launch configuration so that"
    echo " Apptainer/Docker bind-mounts point at the correct host paths:"
    echo ""
    echo "   # TeXLive"
    echo "   HOST_TEXLIVE_BIN=/usr/bin"
    echo "   HOST_TEXMF_DIR=/usr/share/texmf"
    echo "   HOST_TEXLIVE_DIR=/usr/share/texlive"
    echo ""
    echo "   # ImageMagick"
    echo "   HOST_IMAGEMAGICK_BIN=/usr/bin/convert"
    echo "   HOST_IMAGEMAGICK_POLICY=/etc/ImageMagick-6/policy.xml"
    echo ""
    echo " Example Apptainer bind flags:"
    echo "   --bind /usr/share/texmf:/usr/share/texmf:ro"
    echo "   --bind /usr/bin/pdflatex:/usr/bin/pdflatex:ro"
    echo "   --bind /usr/bin/convert:/usr/bin/convert:ro"
    echo "   --bind /etc/ImageMagick-6:/etc/ImageMagick-6:ro"
    echo "=================================================================="
    echo ""
}

# ---------------------------------------------------------------------------
# Argument parsing
# ---------------------------------------------------------------------------

DO_TEXLIVE=false
DO_IMAGEMAGICK=false
DO_CHECK=false

usage() {
    cat <<EOF
Usage: sudo ${SCRIPT_NAME} [OPTIONS]

Options:
  --texlive       Install TeXLive packages only
  --imagemagick   Install ImageMagick only
  --all           Install all packages (default if no flags given)
  --check         Verify tools without installing anything
  -h, --help      Show this help message

If no option is provided, --all is assumed.
EOF
    exit 0
}

parse_args() {
    local explicit=false

    while [[ $# -gt 0 ]]; do
        case "$1" in
        --texlive)
            DO_TEXLIVE=true
            explicit=true
            shift
            ;;
        --imagemagick)
            DO_IMAGEMAGICK=true
            explicit=true
            shift
            ;;
        --all)
            DO_TEXLIVE=true
            DO_IMAGEMAGICK=true
            explicit=true
            shift
            ;;
        --check)
            DO_CHECK=true
            explicit=true
            shift
            ;;
        -h | --help)
            usage
            ;;
        *)
            error "Unknown argument: $1. Use --help for usage."
            ;;
        esac
    done

    # Default: install everything
    if [[ "${explicit}" == false ]]; then
        DO_TEXLIVE=true
        DO_IMAGEMAGICK=true
    fi
}

# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

main() {
    parse_args "$@"

    # --check mode skips installation entirely
    if [[ "${DO_CHECK}" == true ]]; then
        info "Running in --check mode (no packages will be installed)."
        run_verification
        exit $?
    fi

    check_root

    if [[ "${DO_TEXLIVE}" == true ]]; then
        install_texlive
    fi

    if [[ "${DO_IMAGEMAGICK}" == true ]]; then
        install_imagemagick
    fi

    run_verification
    print_env_guidance
}

main "$@"

# EOF
