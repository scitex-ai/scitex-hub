#!/bin/bash
# -*- coding: utf-8 -*-
# Timestamp: "2025-10-20 15:51:12 (ywatanabe)"
# File: ./deployment/gitea/setup_gitea.sh

ORIG_DIR="$(pwd)"
THIS_DIR="$(cd $(dirname ${BASH_SOURCE[0]}) && pwd)"
LOG_PATH="$THIS_DIR/.$(basename $0).log"
echo > "$LOG_PATH"

BLACK='\033[0;30m'
LIGHT_GRAY='\033[0;37m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo_info() { echo -e "${LIGHT_GRAY}$1${NC}"; }
echo_success() { echo -e "${GREEN}$1${NC}"; }
echo_warning() { echo -e "${YELLOW}$1${NC}"; }
echo_error() { echo -e "${RED}$1${NC}"; }
# ---------------------------------------
# Timestamp: 2025-10-20
# Author: ywatanabe

set -e

BLUE='\033[0;34m'
NC='\033[0m'

echo_blue() { echo -e "${BLUE}$1${NC}"; }

GITEA_VERSION="1.21.5"
GITEA_USER="gitea"
GITEA_HOME="/var/lib/gitea"
GITEA_BIN="/usr/local/bin/gitea"
GITEA_CONFIG_DIR="/etc/gitea"

usage() {
    echo "Usage: sudo $0 [-e|--env ENV] [-h|--help]"
    echo ""
    echo "Options:"
    echo "  -e, --env    Environment: dev or prod (required)"
    echo "  -h, --help   Display this help message"
    echo ""
    echo "Example:"
    echo "  sudo $0 -e dev"
    echo "  sudo $0 --env prod"
    exit 1
}

parse_args() {
    ENV=""

    while [[ $# -gt 0 ]]; do
        case $1 in
            -e | --env)
                ENV="$2"
                shift 2
                ;;
            -h | --help)
                usage
                ;;
            *)
                echo_error "Unknown option: $1"
                usage
                ;;
        esac
    done

    if [ -z "$ENV" ]; then
        echo_error "Environment (-e|--env) is required"
        usage
    fi

    if [ "$ENV" != "dev" ] && [ "$ENV" != "prod" ]; then
        echo_error "Environment must be 'dev' or 'prod'"
        usage
    fi
}

set_environment_variables() {
    if [ "$ENV" = "dev" ]; then
        GITEA_DB_NAME="gitea_dev"
        GITEA_DB_USER="gitea_dev"
        DOMAIN="localhost"
        HTTP_PORT="3001"
        SSH_PORT="2223"
        ROOT_URL="http://localhost:${HTTP_PORT}/"
        SERVICE_NAME="gitea_dev"
    else
        GITEA_DB_NAME="gitea_prod"
        GITEA_DB_USER="gitea_prod"
        DOMAIN="git.scitex.ai"
        HTTP_PORT="3000"
        SSH_PORT="2222"
        ROOT_URL="https://${DOMAIN}/"
        SERVICE_NAME="gitea_prod"
    fi
}

check_root() {
    if [ "$EUID" -ne 0 ]; then
        echo_error "This script must be run as root (use sudo)"
        exit 1
    fi
}

check_postgres() {
    echo_info "Checking PostgreSQL status..."
    if ! systemctl is-active --quiet postgresql; then
        echo_error "PostgreSQL is not running. Please start it first."
        exit 1
    fi
    echo_success "PostgreSQL is running"
}

create_gitea_user() {
    echo_info "Creating gitea system user..."
    if id "$GITEA_USER" &> /dev/null; then
        echo_warning "User $GITEA_USER already exists, skipping..."
    else
        useradd --system --shell /bin/bash --home "$GITEA_HOME" "$GITEA_USER"
        echo_success "Created user $GITEA_USER"
    fi
}

create_directories() {
    echo_info "Creating Gitea directories..."
    mkdir -p "$GITEA_HOME"/{custom,data,log}
    mkdir -p "$GITEA_CONFIG_DIR"
    mkdir -p "$GITEA_HOME/data/gitea-repositories"
    mkdir -p "$GITEA_HOME/data/lfs"
    chown -R "$GITEA_USER:$GITEA_USER" "$GITEA_HOME"
    chmod -R 750 "$GITEA_HOME"
    chown root:$GITEA_USER "$GITEA_CONFIG_DIR"
    chmod 770 "$GITEA_CONFIG_DIR"
    echo_success "Directories created"
}

install_gitea_binary() {
    if [ -f "$GITEA_BIN" ]; then
        echo_warning "Gitea binary already exists at $GITEA_BIN"
        "$GITEA_BIN" --version
        return 0
    fi

    echo_info "Downloading Gitea ${GITEA_VERSION}..."
    ARCH=$(uname -m)
    if [ "$ARCH" = "x86_64" ]; then
        ARCH="amd64"
    elif [ "$ARCH" = "aarch64" ]; then
        ARCH="arm64"
    fi
    DOWNLOAD_URL="https://dl.gitea.io/gitea/${GITEA_VERSION}/gitea-${GITEA_VERSION}-linux-${ARCH}"
    wget -O "$GITEA_BIN" "$DOWNLOAD_URL"
    chmod +x "$GITEA_BIN"
    echo_success "Gitea binary installed at $GITEA_BIN"
    "$GITEA_BIN" --version
}

create_database() {
    echo_info "Creating PostgreSQL database for Gitea..."

    local password_file="/root/.gitea_${ENV}_db_password"
    local db_exists=$(sudo -u postgres psql -tAc "SELECT 1 FROM pg_database WHERE datname='$GITEA_DB_NAME'")
    local user_exists=$(sudo -u postgres psql -tAc "SELECT 1 FROM pg_user WHERE usename='$GITEA_DB_USER'")

    if [ "$db_exists" = "1" ] && [ "$user_exists" = "1" ]; then
        echo_warning "Database '$GITEA_DB_NAME' and user '$GITEA_DB_USER' already exist"
        if [ -f "$password_file" ]; then
            # Ensure PostgreSQL password matches the password file
            DB_PASSWORD=$(cat "$password_file")
            echo_info "Syncing PostgreSQL password with password file..."
            sudo -u postgres psql -c "ALTER USER ${GITEA_DB_USER} WITH PASSWORD '${DB_PASSWORD}';"
            echo_success "PostgreSQL password synchronized"
            return 0
        else
            echo_error "Password file missing: $password_file"
            echo "Run to recreate: sudo -u postgres psql -c \"DROP DATABASE ${GITEA_DB_NAME}; DROP USER ${GITEA_DB_USER};\""
            exit 1
        fi
    fi

    DB_PASSWORD=$(openssl rand -base64 32 | tr -d "=+/" | cut -c1-32)
    sudo -u postgres psql << EOF
DO \$\$
BEGIN
    IF NOT EXISTS (SELECT FROM pg_user WHERE usename = '${GITEA_DB_USER}') THEN
        CREATE USER ${GITEA_DB_USER} WITH PASSWORD '${DB_PASSWORD}';
    END IF;
END\$\$;
SELECT 'CREATE DATABASE ${GITEA_DB_NAME} OWNER ${GITEA_DB_USER}'
WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = '${GITEA_DB_NAME}')\gexec
GRANT ALL PRIVILEGES ON DATABASE ${GITEA_DB_NAME} TO ${GITEA_DB_USER};
EOF
    echo "$DB_PASSWORD" > "$password_file"
    chmod 600 "$password_file"
    echo_success "Database created: $GITEA_DB_NAME"
    echo_success "Password saved to $password_file"
}

create_config() {
    echo_info "Creating Gitea configuration..."
    DB_PASSWORD=$(cat "/root/.gitea_${ENV}_db_password")
    SCITEX_CLOUD_DJANGO_SECRET_KEY=$(gitea generate secret SCITEX_CLOUD_DJANGO_SECRET_KEY)
    INTERNAL_TOKEN=$(gitea generate secret INTERNAL_TOKEN)
    JWT_SECRET=$(gitea generate secret JWT_SECRET)
    cat > "${GITEA_CONFIG_DIR}/app_${ENV}.ini" << EOF
[server]
APP_NAME = SciTeX Git Hosting (${ENV})
DOMAIN = ${DOMAIN}
SSH_DOMAIN = ${DOMAIN}
HTTP_PORT = ${HTTP_PORT}
ROOT_URL = ${ROOT_URL}
DISABLE_SSH = false
SSH_PORT = ${SSH_PORT}
SSH_LISTEN_PORT = ${SSH_PORT}
START_SSH_SERVER = true
LFS_START_SERVER = true
LFS_JWT_SECRET = ${JWT_SECRET}
OFFLINE_MODE = false

[database]
DB_TYPE = postgres
HOST = localhost:5432
NAME = ${GITEA_DB_NAME}
USER = ${GITEA_DB_USER}
PASSWD = ${DB_PASSWORD}
SSL_MODE = disable
CHARSET = utf8
PATH = ${GITEA_HOME}/data/gitea.db
LOG_SQL = false

[repository]
ROOT = ${GITEA_HOME}/data/gitea-repositories
SCRIPT_TYPE = bash
DEFAULT_BRANCH = main
DEFAULT_PRIVATE = last
ENABLE_PUSH_CREATE_USER = true
ENABLE_PUSH_CREATE_ORG = true

[security]
INSTALL_LOCK = true
SCITEX_CLOUD_DJANGO_SECRET_KEY = ${SCITEX_CLOUD_DJANGO_SECRET_KEY}
INTERNAL_TOKEN = ${INTERNAL_TOKEN}
PASSWORD_HASH_ALGO = pbkdf2

[service]
DISABLE_REGISTRATION = false
REQUIRE_SIGNIN_VIEW = false
REGISTER_SCITEX_CLOUD_EMAIL_CONFIRM = false
ENABLE_NOTIFY_MAIL = false
ALLOW_ONLY_EXTERNAL_REGISTRATION = false
ENABLE_CAPTCHA = false
DEFAULT_KEEP_SCITEX_CLOUD_EMAIL_PRIVATE = false
DEFAULT_ALLOW_CREATE_ORGANIZATION = true
DEFAULT_ENABLE_TIMETRACKING = true
NO_REPLY_ADDRESS = noreply.${DOMAIN}

[mailer]
ENABLED = false

[session]
PROVIDER = file
PROVIDER_CONFIG = ${GITEA_HOME}/data/sessions

[log]
MODE = console, file
LEVEL = Info
ROOT_PATH = ${GITEA_HOME}/log

[git]
MAX_GIT_DIFF_LINES = 1000
MAX_GIT_DIFF_LINE_CHARACTERS = 5000
MAX_GIT_DIFF_FILES = 100

[api]
ENABLE_SWAGGER = true

[oauth2]
JWT_SECRET = ${JWT_SECRET}

[lfs]
PATH = ${GITEA_HOME}/data/lfs

[actions]
ENABLED = true
EOF
    chown root:$GITEA_USER "${GITEA_CONFIG_DIR}/app_${ENV}.ini"
    chmod 640 "${GITEA_CONFIG_DIR}/app_${ENV}.ini"
    echo_success "Gitea configuration created: app_${ENV}.ini"
}

create_systemd_service() {
    echo_info "Creating systemd service..."
    cat > "/etc/systemd/system/${SERVICE_NAME}.service" << EOF
[Unit]
Description=Gitea (${ENV})
After=syslog.target
After=network.target
After=postgresql.service

[Service]
Type=simple
User=${GITEA_USER}
Group=${GITEA_USER}
WorkingDirectory=${GITEA_HOME}
ExecStart=${GITEA_BIN} web --config ${GITEA_CONFIG_DIR}/app_${ENV}.ini
Restart=always
Environment=USER=${GITEA_USER}
Environment=HOME=${GITEA_HOME}
Environment=GITEA_WORK_DIR=${GITEA_HOME}
ProtectSystem=full
PrivateDevices=yes
PrivateTmp=yes
NoNewPrivileges=true

[Install]
WantedBy=multi-user.target
EOF
    systemctl daemon-reload
    echo_success "Systemd service created: ${SERVICE_NAME}"
}

create_nginx_config() {
    if [ "$ENV" = "dev" ]; then
        echo_info "Skipping Nginx configuration for dev (access directly)"
        return 0
    fi

    echo_info "Setting up Nginx configuration..."

    # Use unified config (like scitex_cloud_prod.conf)
    local nginx_src="$THIS_DIR/gitea_${ENV}.conf"
    local nginx_available="/etc/nginx/sites-available/gitea.conf"
    local nginx_enabled="/etc/nginx/sites-enabled/gitea.conf"

    if [ ! -f "$nginx_src" ]; then
        echo_error "Nginx config not found: $nginx_src"
        exit 1
    fi

    # Remove old configs
    rm -f /etc/nginx/sites-available/gitea* /etc/nginx/sites-enabled/gitea*

    echo_info "Symlinking Nginx configuration..."
    ln -sf "$nginx_src" "$nginx_available"
    ln -sf "$nginx_available" "$nginx_enabled"

    echo_success "Nginx configuration linked: $(basename $nginx_src)"

    # Check if SSL certificate exists
    local ssl_cert="/etc/letsencrypt/live/${DOMAIN}/fullchain.pem"
    if [ ! -f "$ssl_cert" ]; then
        echo ""
        echo_warning "To enable HTTPS, run:"
        echo_warning "  sudo certbot --nginx -d ${DOMAIN}"
        echo_info "Certbot will automatically update SSL certificate paths in the config"
    fi
}

configure_firewall() {
    if [ "$ENV" = "dev" ]; then
        echo_info "Skipping firewall for dev"
        return 0
    fi

    echo_info "Configuring firewall..."
    if command -v ufw &> /dev/null; then
        ufw allow ${HTTP_PORT}/tcp comment "Gitea HTTP"
        ufw allow ${SSH_PORT}/tcp comment "Gitea SSH"
        echo_success "UFW rules added"
    elif command -v firewall-cmd &> /dev/null; then
        firewall-cmd --permanent --add-port=${HTTP_PORT}/tcp
        firewall-cmd --permanent --add-port=${SSH_PORT}/tcp
        firewall-cmd --reload
        echo_success "Firewalld rules added"
    else
        echo_warning "No firewall detected, skipping..."
    fi
}

setup_ssl_certificate() {
    echo_info "Checking SSL certificate..."
    CERT_PATH="/etc/letsencrypt/live/${DOMAIN}/fullchain.pem"

    if [ -f "$CERT_PATH" ]; then
        echo_success "SSL certificate already exists"
        return 0
    fi

    if ! command -v certbot &> /dev/null; then
        echo_warning "Certbot not installed. Installing..."
        apt-get update
        apt-get install -y certbot python3-certbot-nginx
    fi

    echo_info "Running certbot for ${DOMAIN}..."
    certbot --nginx -d "${DOMAIN}" --non-interactive --agree-tos --register-unsafely-without-email

    if [ -f "$CERT_PATH" ]; then
        echo_success "SSL certificate obtained"
        systemctl reload nginx
    else
        echo_warning "SSL certificate setup failed. Run manually: sudo certbot --nginx -d ${DOMAIN}"
    fi
}

start_gitea() {
    echo_info "Starting Gitea service..."
    systemctl enable ${SERVICE_NAME}
    systemctl restart ${SERVICE_NAME}
    sleep 3
    if systemctl is-active --quiet ${SERVICE_NAME}; then
        echo_success "Gitea is running"
    else
        echo_error "Gitea failed to start. Check logs: journalctl -u ${SERVICE_NAME} -n 50"
        exit 1
    fi
}

display_instructions() {
    echo ""
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo_success "Gitea ${ENV} Setup Complete"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo ""
    echo "Access Gitea:"
    if [ "$ENV" = "dev" ]; then
        echo "  http://localhost:${HTTP_PORT}"
    else
        echo "  http://localhost:${HTTP_PORT}"
        echo "  https://${DOMAIN} (after SSL setup)"
        echo ""
        echo "SSL Setup:"
        echo "  sudo certbot --nginx -d ${DOMAIN}"
    fi
    echo ""
    echo "First user to register will be admin"
    echo ""
    echo "Configuration:"
    echo "  Config: ${GITEA_CONFIG_DIR}/app_${ENV}.ini"
    echo "  Data: ${GITEA_HOME}/data/"
    echo "  Logs: ${GITEA_HOME}/log/"
    echo "  DB Password: /root/.gitea_${ENV}_db_password"
    echo ""
    echo "Service Management:"
    echo "  systemctl status ${SERVICE_NAME}"
    echo "  systemctl restart ${SERVICE_NAME}"
    echo "  journalctl -u ${SERVICE_NAME} -f"
    echo ""
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
}

main() {
    parse_args "$@"
    set_environment_variables

    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "  Gitea ${ENV} Setup for SciTeX Cloud"
    echo "  Domain: ${DOMAIN}"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo ""
    check_root
    check_postgres
    create_gitea_user
    create_directories
    install_gitea_binary
    create_database
    create_config
    create_systemd_service
    create_nginx_config
    configure_firewall
    start_gitea
    display_instructions
}

main "$@" 2>&1 | tee -a "$LOG_PATH"

# EOF
