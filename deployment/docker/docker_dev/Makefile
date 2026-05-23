# ============================================
# SciTeX Hub - Docker Development Environment
# ============================================
# Location: /containers/docker_dev/Makefile.dev

.PHONY: \
	help \
	setup \
	build \
	start \
	restart \
	stop \
	down \
	logs \
	ps \
	clean \
	rebuild \
	test \
	test-e2e \
	test-e2e-headed \
	test-e2e-specific \
	migrate \
	makemigrations \
	shell \
	createsuperuser \
	collectstatic \
	db-shell \
	db-reset \
	verify-env \
	docker-check-health \
	logs-django \
	logs-db \
	logs-gitea \
	logs-redis \
	exec-django \
	exec-db \
	exec-gitea \
	gitea-token \
	verify-gitea \
	recreate-testuser \
	list-env \
	clean-python \
	dev \
	update \
	reset

.DEFAULT_GOAL := help

# ============================================
# Variables
# ============================================
COMPOSE := docker compose -f docker-compose.yml
DJANGO_CONTAINER := scitex-hub-dev-django-1
DB_CONTAINER := scitex-hub-dev-db-1
GITEA_CONTAINER := scitex-hub-dev-gitea-1
REDIS_CONTAINER := scitex-hub-dev-redis-1
SCRIPTS_DIR := .

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
	@echo -e "$(GREEN)║          SciTeX Hub - Development Mode              ║$(NC)"
	@echo -e "$(GREEN)╚═══════════════════════════════════════════════════════╝$(NC)"
	@echo -e ""
	@echo -e "$(CYAN)🚀 Quick Start:$(NC)"
	@echo -e "  make start              - Full setup from scratch (recommended)"
	@echo -e "  make restart            - Quick restart of web container"
	@echo -e "  make reload             - Super quick reload (for scitex changes)"
	@echo -e "  make logs               - View all service logs"
	@echo -e "  make stop               - Stop all services"
	@echo -e ""
	@echo -e "$(CYAN)🐳 Docker Services:$(NC)"
	@echo -e "  make build              - Build Docker images"
	@echo -e "  make up                 - Start all services (no rebuild)"
	@echo -e "  make down               - Stop and remove containers"
	@echo -e "  make ps                 - Show service status"
	@echo -e "  make rebuild            - Clean rebuild (stops, builds, starts)"
	@echo -e "  make clean              - Remove containers and volumes (⚠️  DANGEROUS)"
	@echo -e ""
	@echo -e "$(CYAN)🐍 Django Management:$(NC)"
	@echo -e "  make migrate            - Run database migrations"
	@echo -e "  make makemigrations     - Create new migrations"
	@echo -e "  make shell              - Open Django shell"
	@echo -e "  make createsuperuser    - Create superuser account"
	@echo -e "  make collectstatic      - Collect static files"
	@echo -e "  make test               - Run test suite"
	@echo -e ""
	@echo -e "$(CYAN)🗄️  Database:$(NC)"
	@echo -e "  make db-shell           - PostgreSQL shell"
	@echo -e "  make db-reset           - Reset database (⚠️  DELETES ALL DATA)"
	@echo -e ""
	@echo -e "$(CYAN)📋 Logs & Monitoring:$(NC)"
	@echo -e "  make logs               - View all service logs"
	@echo -e "  make logs-django        - View Django container logs"
	@echo -e "  make logs-db            - View database logs"
	@echo -e "  make logs-gitea         - View Gitea logs"
	@echo -e "  make logs-redis         - View Redis logs"
	@echo -e ""
	@echo -e "$(CYAN)🔧 Shell Access:$(NC)"
	@echo -e "  make exec-django        - Shell into Django container"
	@echo -e "  make exec-db            - Shell into database container"
	@echo -e "  make exec-gitea         - Shell into Gitea container"
	@echo -e ""
	@echo -e "$(CYAN)🔑 Gitea Management:$(NC)"
	@echo -e "  make gitea-token        - Generate/verify Gitea API token"
	@echo -e "  make verify-gitea       - Verify Gitea API access"
	@echo -e "  make recreate-testuser  - Recreate test user"
	@echo -e ""
	@echo -e "$(CYAN)🧪 Development Shortcuts:$(NC)"
	@echo -e "  make dev                - Full dev cycle (start + migrate + collectstatic)"
	@echo -e "  make update             - Quick update (restart)"
	@echo -e "  make reset              - Full reset (down + clean + start)"
	@echo -e ""
	@echo -e "$(YELLOW)Access URLs:$(NC)"
	@echo -e "  📍 Django: http://localhost:8000"
	@echo -e "  📍 Gitea:  http://localhost:3000"
	@echo -e ""

# ============================================
# Setup & Build Commands
# ============================================
setup: start migrate collectstatic
	@echo -e "$(GREEN)✅ Development setup complete!$(NC)"

start:
	@echo -e "$(CYAN)🚀 Starting development environment...$(NC)"
	cd $(CURDIR) && bash $(CURDIR)/server.sh -a start

restart:
	@echo -e "$(CYAN)🔄 Restarting web container...$(NC)"
	cd $(CURDIR) && bash $(CURDIR)/server.sh -a restart

reload:
	@echo -e "$(CYAN)⚡ Quick reload (for scitex code changes)...$(NC)"
	$(COMPOSE) restart django
	@echo -e "$(GREEN)✅ Reloaded!$(NC)"

build:
	@echo -e "$(CYAN)🏗️  Building Docker images...$(NC)"
	DOCKER_BUILDKIT=1 COMPOSE_DOCKER_CLI_BUILD=1 $(COMPOSE) build --parallel

build-no-cache:
	@echo -e "$(CYAN)🏗️  Building Docker images (without cache)...$(NC)"
	DOCKER_BUILDKIT=1 COMPOSE_DOCKER_CLI_BUILD=1 $(COMPOSE) build --parallel --no-cache

up:
	@echo -e "$(CYAN)⬆️  Starting services...$(NC)"
	$(COMPOSE) up -d
	@echo -e "$(GREEN)✅ Services started$(NC)"

down:
	@echo -e "$(YELLOW)⬇️  Stopping services...$(NC)"
	$(COMPOSE) down
	@echo -e "$(GREEN)✅ Services stopped$(NC)"

stop: down

ps:
	@echo -e "$(CYAN)📊 Service Status:$(NC)"
	$(COMPOSE) ps

rebuild: down build up migrate collectstatic
	@echo -e "$(GREEN)✅ Rebuild complete!$(NC)"

clean:
	@echo -e "$(RED)⚠️  WARNING: This will remove ALL containers and volumes!$(NC)"
	@read -p "Are you absolutely sure? Type 'yes' to confirm: " confirm && \
	[ "$$confirm" = "yes" ] && \
	(echo "$(RED)🗑️  Removing containers and volumes...$(NC)" && \
	$(COMPOSE) down -v && \
	echo "$(GREEN)✅ Cleanup complete$(NC)") || \
	echo "$(YELLOW)❌ Cleanup cancelled$(NC)"

# ============================================
# Docker Health Check
# ============================================
docker-check-health:
	@if ! docker ps | grep -q $(DJANGO_CONTAINER); then \
		echo "$(RED)❌ Django container ($(DJANGO_CONTAINER)) is not running!$(NC)"; \
		echo "$(YELLOW)Run 'make start' first.$(NC)"; \
		exit 1; \
	fi

# ============================================
# Django Management Commands
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

createsuperuser: docker-check-health
	@echo -e "$(CYAN)👤 Creating superuser...$(NC)"
	$(COMPOSE) exec django python manage.py createsuperuser

# build-ts removed - Vite handles TypeScript directly

collectstatic: docker-check-health
	@echo -e "$(CYAN)📦 Collecting static files...$(NC)"
	$(COMPOSE) exec -T django python manage.py collectstatic --noinput
	@echo -e "$(GREEN)✅ Static files collected$(NC)"

test: docker-check-health
	@echo -e "$(CYAN)🧪 Running tests...$(NC)"
	$(COMPOSE) exec -T django python manage.py test
	@echo -e "$(GREEN)✅ Tests completed$(NC)"

# E2E Testing with Playwright
test-e2e: docker-check-health
	@echo -e "$(CYAN)🎭 Running E2E tests (headless)...$(NC)"
	$(COMPOSE) exec -T django pytest tests/e2e/ -v -p no:zarr
	@echo -e "$(GREEN)✅ E2E tests completed$(NC)"

test-e2e-headed: docker-check-health
	@echo -e "$(CYAN)🎭 Running E2E tests (with browser)...$(NC)"
	@echo -e "$(YELLOW)⚠️  Note: Headed mode requires X11 forwarding in Docker$(NC)"
	$(COMPOSE) exec -T -e DISPLAY=$(DISPLAY) django pytest tests/e2e/ -v --headed --browser chromium
	@echo -e "$(GREEN)✅ E2E tests completed$(NC)"

test-e2e-specific: docker-check-health
	@if [ -z "$(TEST)" ]; then \
		echo "$(RED)❌ TEST not specified!$(NC)"; \
		echo "$(YELLOW)Usage: make test-e2e-specific TEST=tests/e2e/test_user_creation.py$(NC)"; \
		exit 1; \
	fi
	@echo -e "$(CYAN)🎭 Running specific E2E test: $(TEST)...$(NC)"
	$(COMPOSE) exec -T django pytest $(TEST) -v -p no:zarr
	@echo -e "$(GREEN)✅ E2E test completed$(NC)"

# ============================================
# Database Commands
# ============================================
db-shell: docker-check-health
	@echo -e "$(CYAN)🗄️  Opening PostgreSQL shell...$(NC)"
	@$(COMPOSE) exec db psql -U $${SCITEX_HUB_POSTGRES_USER:-scitex_dev} -d $${SCITEX_HUB_POSTGRES_DB:-scitex_hub_dev}

db-reset: docker-check-health
	@echo -e "$(RED)⚠️  WARNING: This will DELETE ALL DATA in the database!$(NC)"
	@read -p "Are you absolutely sure? Type 'yes' to confirm: " confirm && \
	[ "$$confirm" = "yes" ] && \
	(echo "$(RED)🔄 Resetting database...$(NC)" && \
	$(COMPOSE) exec -T django python manage.py flush --noinput && \
	$(COMPOSE) exec -T django python manage.py migrate && \
	echo "$(GREEN)✅ Database reset complete$(NC)") || \
	echo "$(YELLOW)❌ Database reset cancelled$(NC)"

# ============================================
# Logs & Monitoring
# ============================================
logs:
	@echo -e "$(CYAN)📋 Showing all service logs (Ctrl+C to exit)...$(NC)"
	$(COMPOSE) logs -f

logs-django:
	@echo -e "$(CYAN)📋 Showing Django container logs...$(NC)"
	$(COMPOSE) logs -f django

logs-db:
	@echo -e "$(CYAN)📋 Showing database logs...$(NC)"
	$(COMPOSE) logs -f db

logs-gitea:
	@echo -e "$(CYAN)📋 Showing Gitea logs...$(NC)"
	$(COMPOSE) logs -f gitea

logs-redis:
	@echo -e "$(CYAN)📋 Showing Redis logs...$(NC)"
	$(COMPOSE) logs -f redis

# ============================================
# Shell Access
# ============================================
exec-django: docker-check-health
	@echo -e "$(CYAN)🐳 Opening shell in Django container...$(NC)"
	$(COMPOSE) exec django /bin/bash

exec-db: docker-check-health
	@echo -e "$(CYAN)🐳 Opening shell in database container...$(NC)"
	$(COMPOSE) exec db /bin/sh

exec-gitea: docker-check-health
	@echo -e "$(CYAN)🐳 Opening shell in Gitea container...$(NC)"
	$(COMPOSE) exec gitea /bin/sh

# ============================================
# Gitea Management
# ============================================
gitea-token: docker-check-health
	@echo -e "$(CYAN)🔑 Setting up Gitea API token...$(NC)"
	cd $(CURDIR) && bash $(CURDIR)/server.sh -a setup_gitea_token

verify-gitea: docker-check-health
	@echo -e "$(CYAN)🔍 Verifying Gitea API access...$(NC)"
	cd $(CURDIR) && bash $(CURDIR)/server.sh -a verify_gitea_api

recreate-testuser: docker-check-health
	@echo -e "$(CYAN)👤 Recreating test user...$(NC)"
	cd $(CURDIR) && bash $(CURDIR)/server.sh -a recreate_test_user

# ============================================
# Environment & Utilities
# ============================================
verify-env:
	@echo -e "$(CYAN)🔍 Verifying environment setup...$(NC)"
	cd $(CURDIR) && bash $(CURDIR)/server.sh -a verify_env_setup

list-env:
	@echo -e "$(CYAN)📝 Environment Variables:$(NC)"
	cd $(CURDIR) && bash $(CURDIR)/server.sh -a list_env

clean-python:
	@echo -e "$(CYAN)🧹 Cleaning Python cache files...$(NC)"
	find ../../ -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find ../../ -type f -name "*.pyc" -delete
	find ../../ -type d -name .pytest_cache -exec rm -rf {} + 2>/dev/null || true
	@echo -e "$(GREEN)✅ Python cache cleaned$(NC)"

# ============================================
# Development Workflow Shortcuts
# ============================================
dev: start migrate collectstatic
	@echo -e "$(GREEN)✅ Development environment ready!$(NC)"
	@echo -e "$(GREEN)📍 Django: http://localhost:8000$(NC)"
	@echo -e "$(GREEN)📍 Gitea:  http://localhost:3000$(NC)"

update: restart
	@echo -e "$(GREEN)✅ Services updated$(NC)"

reset: down clean start migrate collectstatic
	@echo -e "$(GREEN)✅ Environment reset complete$(NC)"

# EOF
