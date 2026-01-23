#!/bin/bash
# -*- coding: utf-8 -*-
# Timestamp: "2025-10-20 14:34:26 (ywatanabe)"
# File: ./deployment/postgres/setup_postgres.sh

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

# PostgreSQL Setup Script for SciTeX Cloud (Dev & Prod)

set -e

LOG_FILE=".$(basename $0).log"

usage() {
    echo "Usage: $0 [-e|--env ENV] [-d|--database NAME] [-u|--user NAME] [-p|--password PASS] [-h|--help]"
    echo ""
    echo "Options:"
    echo "  -e, --env        Environment: dev or prod (required)"
    echo "  -d, --database   Database name (optional, defaults based on env)"
    echo "  -u, --user       Database user (optional, defaults based on env)"
    echo "  -p, --password   Database password (optional, defaults based on env)"
    echo "  -h, --help       Display this help message"
    echo ""
    echo "Example:"
    echo "  $0 -e dev"
    echo "  $0 --env prod --password my_secure_password"
    exit 1
}

check_postgres_user() {
    if [ "$USER" != "postgres" ]; then
        echo "ERROR: This script should be run as postgres user:"
        echo "  sudo -u postgres bash $0 $@"
        exit 1
    fi
}

check_existing_database() {
    local db_name="$1"
    local db_user="$2"

    local db_exists=$(psql -tAc "SELECT 1 FROM pg_database WHERE datname='$db_name'")
    local user_exists=$(psql -tAc "SELECT 1 FROM pg_user WHERE usename='$db_user'")

    if [ "$db_exists" = "1" ] || [ "$user_exists" = "1" ]; then
        echo_warning "WARNING: Database '$db_name' or user '$db_user' already exists!"
        echo ""
        echo "To remove them manually, run:"
        echo "  sudo -u postgres psql"
        echo ""
        echo "Then execute:"
        if [ "$db_exists" = "1" ]; then
            echo "  -- Create backup first:"
            echo "  \! pg_dump $db_name > /tmp/${db_name}_backup_\$(date +%Y%m%d_%H%M%S).sql"
            echo "  -- Then drop:"
            echo "  DROP DATABASE IF EXISTS $db_name;"
        fi
        if [ "$user_exists" = "1" ]; then
            echo "  DROP USER IF EXISTS $db_user;"
        fi
        echo ""
        echo -n "Do you want to continue and potentially overwrite? (yes/no): "
        read -r response
        if [ "$response" != "yes" ]; then
            echo_error "Aborted by user"
            exit 1
        fi
    fi
}

create_database_and_user() {
    local db_name="$1"
    local db_user="$2"
    local db_pass="$3"

    echo "Creating database: $db_name"
    echo "Creating user: $db_user"
    echo ""

    psql << EOF
-- Commented out for safety. Uncomment only if you want to drop existing DB/user
-- After backing up: pg_dump $db_name > /tmp/${db_name}_backup_\$(date +%Y%m%d_%H%M%S).sql
-- DROP DATABASE IF EXISTS $db_name;
-- DROP USER IF EXISTS $db_user;

CREATE USER $db_user WITH PASSWORD '$db_pass';
CREATE DATABASE $db_name OWNER $db_user;
GRANT ALL PRIVILEGES ON DATABASE $db_name TO $db_user;
ALTER DATABASE $db_name OWNER TO $db_user;
EOF

    echo "✅ Database and user created"
}

setup_extensions() {
    local db_name="$1"
    local db_user="$2"

    echo "Installing extensions..."

    psql -d "$db_name" << EOF
CREATE EXTENSION IF NOT EXISTS pg_trgm;
CREATE EXTENSION IF NOT EXISTS unaccent;
GRANT ALL ON SCHEMA public TO $db_user;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON TABLES TO $db_user;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON SEQUENCES TO $db_user;
EOF

    echo "✅ Extensions installed"
}

verify_setup() {
    local db_name="$1"
    local db_user="$2"

    echo ""
    echo "Verifying setup..."

    psql << EOF
\l $db_name
\du $db_user
\c $db_name
\dx
EOF
}

print_summary() {
    local env="$1"
    local db_name="$2"
    local db_user="$3"
    local db_pass="$4"

    echo ""
    echo "✅ PostgreSQL $env setup complete!"
    echo ""
    echo "Database credentials:"
    echo "  Database: $db_name"
    echo "  User: $db_user"
    echo "  Password: $db_pass"
    echo ""
    echo "Next steps:"
    echo "1. Update .env file with database credentials"
    echo "2. Run: python manage.py migrate"
    if [ "$env" = "prod" ]; then
        echo "3. Run: python manage.py createsuperuser"
    fi
}

parse_args() {
    ENV=""
    DB_NAME=""
    DB_USER=""
    DB_PASS=""

    while [[ $# -gt 0 ]]; do
        case $1 in
            -e | --env)
                ENV="$2"
                shift 2
                ;;
            -d | --database)
                DB_NAME="$2"
                shift 2
                ;;
            -u | --user)
                DB_USER="$2"
                shift 2
                ;;
            -p | --password)
                DB_PASS="$2"
                shift 2
                ;;
            -h | --help)
                usage
                ;;
            *)
                echo "Unknown option: $1"
                usage
                ;;
        esac
    done

    if [ -z "$ENV" ]; then
        echo "ERROR: Environment (-e|--env) is required"
        usage
    fi

    if [ "$ENV" != "dev" ] && [ "$ENV" != "prod" ]; then
        echo "ERROR: Environment must be 'dev' or 'prod'"
        usage
    fi

    if [ -z "$DB_NAME" ]; then
        DB_NAME="scitex_cloud_$ENV"
    fi

    if [ -z "$DB_USER" ]; then
        DB_USER="scitex_$ENV"
    fi

    if [ -z "$DB_PASS" ]; then
        if [ "$ENV" = "dev" ]; then
            DB_PASS="scitex_dev_2025"
        else
            DB_PASS="${SCITEX_CLOUD_DB_PASSWORD_PROD:-CHANGE_THIS_PASSWORD}"
        fi
    fi
}

main() {
    echo "=== SciTeX Cloud PostgreSQL Setup ==="
    echo ""

    parse_args "$@"
    check_postgres_user
    check_existing_database "$DB_NAME" "$DB_USER"
    create_database_and_user "$DB_NAME" "$DB_USER" "$DB_PASS"
    setup_extensions "$DB_NAME" "$DB_USER"
    verify_setup "$DB_NAME" "$DB_USER"
    print_summary "$ENV" "$DB_NAME" "$DB_USER" "$DB_PASS"
}

main "$@" 2>&1 | tee "$LOG_FILE"

# EOF
