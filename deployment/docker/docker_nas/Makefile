# ============================================
# SciTeX Cloud - Docker NAS Deployment
# ============================================
# Location: /containers/docker_nas/Makefile.nas

.PHONY: help setup build build-no-cache start restart stop down logs ps status rebuild clean-static migrate makemigrations shell collectstatic db-shell db-backup verify-health logs-django logs-db logs-redis exec-django exec-db clean-python cache-purge cache-purge-all cache-purge-static

.DEFAULT_GOAL := help

# ============================================
# Variables
# ============================================
COMPOSE := docker compose -f docker-compose.yml
DJANGO_CONTAINER := scitex-cloud-nas-django-1
DB_CONTAINER := scitex-cloud-nas-db-1
REDIS_CONTAINER := scitex-cloud-nas-redis-1
MAKEFILE_DIR := $(dir $(abspath $(lastword $(MAKEFILE_LIST))))
SCRIPTS_DIR := $(MAKEFILE_DIR)../common/scripts

# Colors for output
GREEN := \033[0;32m
YELLOW := \033[0;33m
RED := \033[0;31m
CYAN := \033[0;36m
NC := \033[0m

# ============================================
# Help (default target)
# ============================================
help:
	@echo -e ""
	@echo -e "$(GREEN)╔═══════════════════════════════════════════════════════╗$(NC)"
	@echo -e "$(GREEN)║           SciTeX Cloud - NAS Deployment               ║$(NC)"
	@echo -e "$(GREEN)╚═══════════════════════════════════════════════════════╝$(NC)"
	@echo -e ""
	@echo -e "$(YELLOW)📦 NAS-optimized deployment for home/lab servers$(NC)"
	@echo -e ""
	@echo -e "$(CYAN)🚀 Deployment:$(NC)"
	@echo -e "  make start              - Start NAS services"
	@echo -e "  make restart            - Restart services"
	@echo -e "  make stop               - Stop all services"
	@echo -e "  make status             - Show service status"
	@echo -e ""
	@echo -e "$(CYAN)🐳 Docker Management:$(NC)"
	@echo -e "  make build              - Build Docker images"
	@echo -e "  make build-no-cache     - Build images without cache (full rebuild)"
	@echo -e "  make up                 - Start services (no rebuild)"
	@echo -e "  make down               - Stop and remove containers"
	@echo -e "  make ps                 - Show container status"
	@echo -e "  make rebuild            - Clean rebuild (clears static volume)"
	@echo -e "  make clean-static       - Clear static files volume only"
	@echo -e ""
	@echo -e "$(CYAN)🐍 Django Management:$(NC)"
	@echo -e "  make migrate            - Run database migrations"
	@echo -e "  make makemigrations     - Create new migrations"
	@echo -e "  make shell              - Open Django shell"
	@echo -e "  make collectstatic      - Collect static files"
	@echo -e ""
	@echo -e "$(CYAN)🗄️  Database:$(NC)"
	@echo -e "  make db-shell           - PostgreSQL shell"
	@echo -e "  make db-backup          - Backup database"
	@echo -e ""
	@echo -e "$(CYAN)📋 Logs & Monitoring:$(NC)"
	@echo -e "  make logs               - View all service logs"
	@echo -e "  make logs-django        - View Django container logs"
	@echo -e "  make logs-db            - View database logs"
	@echo -e "  make logs-redis         - View Redis logs"
	@echo -e ""
	@echo -e "$(CYAN)🔧 Shell Access:$(NC)"
	@echo -e "  make exec-django        - Shell into Django container"
	@echo -e "  make exec-db            - Shell into database container"
	@echo -e ""
	@echo -e "$(CYAN)🔍 Health & Monitoring:$(NC)"
	@echo -e "  make verify-health      - Check all services health"
	@echo -e ""
	@echo -e "$(CYAN)☁️  Cloudflare Cache:$(NC)"
	@echo -e "  make cache-purge        - Purge static files cache (after deploy)"
	@echo -e "  make cache-purge-all    - Purge entire Cloudflare cache"
	@echo -e ""

# ============================================
# Health Check
# ============================================
docker-check-health:
	@if ! docker ps | grep -q "$(DJANGO_CONTAINER)"; then \
		echo -e "$(RED)❌ Django container not running!$(NC)"; \
		echo -e "$(YELLOW)Run 'make start' first.$(NC)"; \
		exit 1; \
	fi

# ============================================
# Deployment Commands
# ============================================
setup: build up migrate collectstatic
	@echo -e "$(GREEN)✅ NAS setup complete!$(NC)"

start:
	@echo -e "$(CYAN)🚀 Starting NAS services (will build if needed)...$(NC)"
	$(COMPOSE) up -d --build
	@echo -e "$(GREEN)✅ NAS services started$(NC)"

restart:
	@echo -e "$(CYAN)🔄 Restarting NAS services...$(NC)"
	$(COMPOSE) restart
	@# Reload nginx to refresh DNS cache (prevents 502 after container IP changes)
	@sleep 2 && docker exec scitex-cloud-nas-nginx-1 nginx -s reload 2>/dev/null || true
	@echo -e "$(GREEN)✅ Services restarted$(NC)"

stop: down

build:
	@echo -e "$(CYAN)🏗️  Building NAS images...$(NC)"
	$(COMPOSE) build
	@echo -e "$(GREEN)✅ Build complete$(NC)"

build-no-cache:
	@echo -e "$(CYAN)🏗️  Building NAS images (no cache)...$(NC)"
	@echo -e "$(YELLOW)⚠️  This will rebuild from scratch and may take longer.$(NC)"
	$(COMPOSE) build --no-cache
	@echo -e "$(GREEN)✅ Build complete$(NC)"

up:
	@echo -e "$(CYAN)⬆️  Starting NAS services...$(NC)"
	$(COMPOSE) up -d
	@echo -e "$(GREEN)✅ Services started$(NC)"

down:
	@echo -e "$(YELLOW)⬇️  Stopping NAS services...$(NC)"
	$(COMPOSE) down
	@echo -e "$(GREEN)✅ Services stopped$(NC)"

ps:
	@echo -e "$(CYAN)📊 Container Status:$(NC)"
	$(COMPOSE) ps

status: ps verify-health

rebuild: down clean-static build up migrate collectstatic cache-purge-static
	@echo -e "$(GREEN)✅ Rebuild complete$(NC)"

clean-static:
	@echo -e "$(CYAN)🧹 Clearing static files volume...$(NC)"
	@docker volume rm scitex-cloud-nas_static_volume 2>/dev/null || true
	@echo -e "$(GREEN)✅ Static volume cleared$(NC)"

# ============================================
# Cloudflare Cache Management
# ============================================
cache-purge: cache-purge-static

cache-purge-static:
	@echo -e "$(CYAN)☁️  Purging Cloudflare static cache...$(NC)"
	@bash "$(SCRIPTS_DIR)/cloudflare_cache_purge.sh" static || echo -e "$(YELLOW)⚠️  Cache purge skipped (credentials not configured)$(NC)"

cache-purge-all:
	@echo -e "$(CYAN)☁️  Purging ALL Cloudflare cache...$(NC)"
	@bash "$(SCRIPTS_DIR)/cloudflare_cache_purge.sh" all || echo -e "$(YELLOW)⚠️  Cache purge skipped (credentials not configured)$(NC)"

# ============================================
# Django Management
# ============================================
migrate: docker-check-health
	@echo -e "$(CYAN)🔄 Running migrations...$(NC)"
	$(COMPOSE) exec -T django python manage.py migrate
	@echo -e "$(GREEN)✅ Migrations applied$(NC)"

makemigrations: docker-check-health
	@echo -e "$(CYAN)📝 Creating migrations...$(NC)"
	$(COMPOSE) exec -T django python manage.py makemigrations
	@echo -e "$(GREEN)✅ Migrations created$(NC)"

shell: docker-check-health
	@echo -e "$(CYAN)🐍 Opening Django shell...$(NC)"
	$(COMPOSE) exec django python manage.py shell

collectstatic: docker-check-health
	@echo -e "$(CYAN)📦 Collecting static files...$(NC)"
	$(COMPOSE) exec -T django python manage.py collectstatic --noinput
	@echo -e "$(GREEN)✅ Static files collected$(NC)"

# ============================================
# Database Commands
# ============================================
db-shell: docker-check-health
	@echo -e "$(CYAN)🗄️  Opening PostgreSQL shell...$(NC)"
	@$(COMPOSE) exec db psql -U $${SCITEX_CLOUD_POSTGRES_USER} -d $${SCITEX_CLOUD_POSTGRES_DB}

db-backup: docker-check-health
	@echo -e "$(CYAN)💾 Backing up NAS database...$(NC)"
	@mkdir -p ../../backups
	@BACKUP_FILE="../../backups/scitex_nas_$$(date +%Y%m%d_%H%M%S).sql" && \
	$(COMPOSE) exec -T db pg_dump -U $${SCITEX_CLOUD_POSTGRES_USER} $${SCITEX_CLOUD_POSTGRES_DB} > $$BACKUP_FILE && \
	gzip $$BACKUP_FILE && \
	echo -e "$(GREEN)✅ Backup saved to: $$BACKUP_FILE.gz$(NC)"

# ============================================
# Logs & Monitoring
# ============================================
logs:
	@echo -e "$(CYAN)📋 Showing NAS logs (Ctrl+C to exit)...$(NC)"
	$(COMPOSE) logs -f --tail=100

logs-django:
	@echo -e "$(CYAN)📋 Showing Django logs...$(NC)"
	$(COMPOSE) logs -f --tail=100 django

logs-db:
	@echo -e "$(CYAN)📋 Showing database logs...$(NC)"
	$(COMPOSE) logs -f --tail=100 db

logs-redis:
	@echo -e "$(CYAN)📋 Showing Redis logs...$(NC)"
	$(COMPOSE) logs -f --tail=100 redis

# ============================================
# Shell Access
# ============================================
exec-django: docker-check-health
	@echo -e "$(CYAN)🐳 Opening shell in Django container...$(NC)"
	$(COMPOSE) exec django /bin/bash

exec-db: docker-check-health
	@echo -e "$(CYAN)🐳 Opening shell in database container...$(NC)"
	$(COMPOSE) exec db /bin/sh

# ============================================
# Health & Monitoring
# ============================================
verify-health:
	@echo -e "$(CYAN)🔍 Checking service health...$(NC)"
	@$(COMPOSE) ps | grep -E "(healthy|Up)" && \
		echo -e "$(GREEN)✅ All services healthy$(NC)" || \
		echo -e "$(RED)❌ Some services unhealthy$(NC)"

# ============================================
# Utilities
# ============================================
clean-python:
	@echo -e "$(CYAN)🧹 Cleaning Python cache files...$(NC)"
	find ../../ -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find ../../ -type f -name "*.pyc" -delete
	@echo -e "$(GREEN)✅ Python cache cleaned$(NC)"

# EOF
