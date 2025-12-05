#!/bin/bash
# -*- coding: utf-8 -*-
# Timestamp: "2025-10-27 14:37:09 (ywatanabe)"
# File: ./containers/docker/install_docker.sh

ORIG_DIR="$(pwd)"
THIS_DIR="$(cd $(dirname ${BASH_SOURCE[0]}) && pwd)"
LOG_PATH="$THIS_DIR/.$(basename $0).log"
echo -e > "$LOG_PATH"

GIT_ROOT="$(git rev-parse --show-toplevel 2> /dev/null)"

GRAY='\033[0;90m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo_info() { echo -e "${GRAY}INFO: $1${NC}"; }
echo_success() { echo -e "${GREEN}SUCC: $1${NC}"; }
echo_warning() { echo -e "${YELLOW}WARN: $1${NC}"; }
echo_error() { echo -e "${RED}ERRO: $1${NC}"; }
echo_header() { echo_info "=== $1 ==="; }
# ---------------------------------------

NC='\033[0m'

readonly DOCKER_GROUP="docker"
set -e

check_docker_installed() {
    command -v docker &> /dev/null
}

check_compose_v2_installed() {
    docker compose version &> /dev/null
}

check_buildx_installed() {
    docker buildx version &> /dev/null
}

install_docker_official() {
    echo_info "Installing Docker from official repository..."
    echo_info "Removing old Docker packages if present..."
    sudo apt-get remove -y docker docker-engine docker.io containerd runc 2> /dev/null || true

    echo_info "Updating package index..."
    sudo apt-get update

    echo_info "Installing prerequisites..."
    sudo apt-get install -y ca-certificates curl gnupg lsb-release

    echo_info "Adding Docker GPG key..."
    sudo mkdir -p /etc/apt/keyrings
    curl -fsSL https://download.docker.com/linux/ubuntu/gpg \
        | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg

    echo_info "Setting up Docker repository..."
    echo -e "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu $(lsb_release -cs) stable" \
        | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null

    echo_info "Installing Docker Engine..."
    sudo apt-get update
    sudo apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin

    echo_success "Docker Engine installed"
}

install_docker_simple() {
    echo_info "Installing Docker from Ubuntu repository..."
    sudo apt-get update
    sudo apt-get install -y docker.io docker-compose-plugin docker-buildx-plugin
    echo_success "Docker installed"
}

setup_user_permissions() {
    echo_info "Setting up user permissions..."

    if ! getent group $DOCKER_GROUP &> /dev/null; then
        sudo groupadd $DOCKER_GROUP
    fi

    sudo usermod -aG $DOCKER_GROUP "$USER"
    echo_success "User added to docker group"
    echo_warning "Log out and log back in for group changes"
    echo_warning "Or run: newgrp docker"
}

remove_old_compose() {
    echo_info "Removing old docker-compose (standalone)..."
    sudo apt-get remove -y docker-compose 2> /dev/null || true
    pip uninstall -y docker-compose 2> /dev/null || true
    sudo rm -f /usr/local/bin/docker-compose
    echo_success "Old docker-compose removed"
}

remove_old_user_plugins() {
    echo_info "Removing old user-installed Docker CLI plugins..."

    # Remove old buildx plugin from user directory (takes precedence over system)
    if [ -f ~/.docker/cli-plugins/docker-buildx ]; then
        echo_info "Removing old buildx from ~/.docker/cli-plugins/"
        rm -f ~/.docker/cli-plugins/docker-buildx
        echo_success "Old user buildx plugin removed"
    fi

    # Remove old compose plugin from user directory if exists
    if [ -f ~/.docker/cli-plugins/docker-compose ]; then
        echo_info "Removing old compose from ~/.docker/cli-plugins/"
        rm -f ~/.docker/cli-plugins/docker-compose
        echo_success "Old user compose plugin removed"
    fi
}

restart_docker_daemon() {
    echo_info "Restarting Docker daemon to load new plugins..."

    # Check if running in WSL
    if grep -qi microsoft /proc/version; then
        echo_info "WSL detected, restarting Docker service..."
        sudo service docker restart
    else
        sudo systemctl restart docker
        sudo systemctl enable docker
    fi

    # Wait for daemon to be ready
    sleep 2
    echo_success "Docker daemon restarted"
}

verify_installation() {
    echo_header "Verifying installation"

    if check_docker_installed; then
        echo_success "Docker: $(docker --version)"
    else
        echo_error "Docker not found"
        return 1
    fi

    if check_compose_v2_installed; then
        echo_success "Docker Compose: $(docker compose version)"
    else
        echo_warning "Docker Compose V2 not found"
    fi

    if check_buildx_installed; then
        echo_success "Docker Buildx: $(docker buildx version)"
    else
        echo_warning "Docker Buildx not found"
    fi

    if sudo docker ps &> /dev/null; then
        echo_success "Docker daemon is running"
    else
        echo_warning "Docker daemon not running, starting..."
        if grep -qi microsoft /proc/version; then
            sudo service docker start
        else
            sudo systemctl start docker
            sudo systemctl enable docker
        fi
    fi
}

main() {
    echo_header "Docker Installation"

    if check_docker_installed; then
        echo_warning "Docker already installed: $(docker --version)"

        # Check if plugins need installation or upgrade
        if ! check_compose_v2_installed || ! check_buildx_installed; then
            echo_info "Installing missing plugins from official repository..."
            install_docker_official
        else
            echo_info "Checking if plugins need upgrade..."
            echo_warning "To upgrade plugins, using official Docker repository..."
            install_docker_official
        fi
    else
        echo_info "Choose installation method:"
        echo -e "  1) Official Docker repository (recommended)"
        echo -e "  2) Ubuntu repository (simpler)"
        read -p "Enter choice [1-2]: " choice_

        case $choice_ in
            1) install_docker_official ;;
            2) install_docker_simple ;;
            *) install_docker_official ;;
        esac

        setup_user_permissions
    fi

    remove_old_compose
    remove_old_user_plugins
    restart_docker_daemon
    verify_installation

    echo_header "Installation Complete"
    echo_info "Next steps:"
    echo_info "  1. Log out and log back in (or: newgrp docker)"
    echo_info "  2. Test: docker run hello-world"
    echo_info "  3. Test: docker compose version"
    echo_info "  4. Test: docker buildx version"
}

main "$@" 2>&1 | tee "$LOG_PATH"

# EOF
