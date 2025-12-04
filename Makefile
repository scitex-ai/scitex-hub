# ============================================
# SciTeX Cloud - Environment Orchestrator
# ============================================
# Exclusive environment management for dev/nas
# Location: /Makefile
#
# Key Features:
# - Mutual exclusivity (only one environment runs at a time)
# - Mandatory environment specification (NO defaults!)
# - State file + Docker reality validation
# - Conflict detection and prevention
# - Safety confirmations for NAS deployment
#
# Usage:
#   make status                    # Show active environment
#   make ENV=dev start             # Start dev (stops others first)
#   make ENV=nas switch            # Switch to NAS
#   make ENV=nas rebuild           # Rebuild NAS (with confirmation)

.PHONY: \
	help \
	status \
	validate-docker \
	validate \
	switch \
	stop-all \
	start \
	restart \
	reload \
	stop \
	down \
	logs \
	ps \
	migrate \
	shell \
	force-stop-all \
	ssl-setup \
	ssl-verify \
	ssl-check \
	ssl-renew \
	verify-health \
	list-envs \
	exec-web \
	exec-db \
	exec-gitea \
	gitea-token \
	recreate-testuser \
	collectstatic \
	makemigrations \
	createsuperuser \
	db-shell \
	db-backup \
	db-reset \
	fresh-start \
	fresh-start-confirm \
	logs-web \
	logs-db \
	logs-gitea \
	build \
	rebuild \
	rebuild-no-cache \
	setup \
	test \
	test-e2e \
	test-e2e-headed \
	test-e2e-specific \
	clean-python \
	clean-js \
	format \
	format-python \
	format-web \
	format-shell \
	lint \
	lint-web \
	check-file-sizes \
	info

.DEFAULT_GOAL := help

# ============================================
# Configuration
# ============================================
VALID_ENVS := dev nas

# Colors
GREEN := \033[0;32m
YELLOW := \033[0;33m
RED := \033[0;31m
CYAN := \033[0;36m
BLUE := \033[0;34m
NC := \033[0m

# ============================================
# Environment Validation - NO DEFAULTS!
# ============================================
# Accept both env= and ENV= (convert lowercase to uppercase)
ifdef env
  ENV := $(env)
endif

# Check if ENV is specified and valid
ifdef ENV
  ifeq ($(filter $(ENV),$(VALID_ENVS)),)
    $(error Invalid ENV='$(ENV)'. Must be one of: dev, nas)
  endif
  DOCKER_DIR := deployment/docker/docker_$(ENV)
  MAKEFILE := $(DOCKER_DIR)/Makefile
else
  # ENV not specified - only allow non-operational commands
  ifneq ($(MAKECMDGOALS),)
    ifneq ($(filter-out help status validate-docker stop-all force-stop-all format format-python format-web format-shell lint lint-web check-file-sizes slurm-start slurm-stop slurm-restart slurm-status slurm-fix slurm-resume slurm-reset info,$(MAKECMDGOALS)),)
      $(error ❌ ENV not specified! Use: make ENV=<dev|nas> <command>)
    endif
  endif
endif

# ============================================
# Docker Reality Detection
# ============================================
# Detect which environments are actually running in Docker
get-running-envs = $(shell docker ps --format '{{.Names}}' 2>/dev/null | grep -oE 'scitex-cloud-(dev|prod|nas)-' | sed 's/scitex-cloud-//' | sed 's/-//' | sort -u)

# ============================================
# Validation Functions
# ============================================
validate-docker:
	@echo "$(CYAN)🔍 Checking for container conflicts...$(NC)"
	@RUNNING=$$(docker ps --format '{{.Names}}' 2>/dev/null | grep -oE 'scitex-cloud-(dev|prod|nas)-' | sed 's/scitex-cloud-//' | sed 's/-//' | sort -u); \
	COUNT=$$(echo "$$RUNNING" | wc -w); \
	if [ $$COUNT -gt 1 ]; then \
		echo "$(RED)❌ CONFLICT: Multiple environments running:$(NC)"; \
		for env in $$RUNNING; do \
			echo "  - $$env"; \
		done; \
		echo "$(YELLOW)   Run 'make stop-all' to clean up$(NC)"; \
		exit 1; \
	fi; \
	if [ $$COUNT -eq 0 ]; then \
		echo "$(GREEN)✅ No containers running$(NC)"; \
	else \
		echo "$(GREEN)✅ Only $$RUNNING is running$(NC)"; \
	fi

# Validation alias
validate: validate-docker

# ============================================
# Help
# ============================================
help:
	@echo ""
	@echo "$(GREEN)╔═══════════════════════════════════════════════════════╗$(NC)"
	@echo "$(GREEN)║      SciTeX Cloud - Environment Orchestrator          ║$(NC)"
	@echo "$(GREEN)╚═══════════════════════════════════════════════════════╝$(NC)"
	@echo ""
	@$(MAKE) --no-print-directory status
	@echo ""
	@echo "$(CYAN)📋 Core Commands:$(NC)"
	@echo "  make status                       # Show active environment"
	@echo "  make validate                     # Validate state consistency"
	@echo "  make ENV=<env> start              # Start environment (stops others)"
	@echo "  make ENV=<env> switch             # Switch environment cleanly"
	@echo "  make ENV=<env> stop               # Stop specific environment"
	@echo "  make stop-all                     # Stop all environments"
	@echo ""
	@echo "$(CYAN)🔧 Build & Deploy:$(NC)"
	@echo "  make ENV=<env> build              # Build images"
	@echo "  make ENV=<env> rebuild            # Rebuild (stops, builds, starts)"
	@echo "  make ENV=<env> rebuild-no-cache   # Rebuild without cache (for dependency fixes)"
	@echo "  make ENV=<env> setup              # Full setup (build + migrate)"
	@echo ""
	@echo "$(CYAN)🐍 Django:$(NC)"
	@echo "  make ENV=<env> migrate            # Run migrations"
	@echo "  make ENV=<env> shell              # Django shell"
	@echo "  make ENV=<env> collectstatic      # Collect static files"
	@echo ""
	@echo "$(CYAN)🔄 Reset & Fresh Start:$(NC)"
	@echo "  make ENV=dev fresh-start          # Complete reset: DB + Gitea + Files (dev only)"
	@echo "  make ENV=dev fresh-start-confirm  # Skip confirmation (use with caution)"
	@echo ""
	@echo "$(CYAN)📊 Monitoring:$(NC)"
	@echo "  make ENV=<env> logs               # View logs"
	@echo "  make ENV=<env> ps                 # Container status"
	@echo ""
	@echo "$(CYAN)💡 Examples:$(NC)"
	@echo "  make status                       # Check what's running"
	@echo "  make ENV=dev start                # Start development"
	@echo "  make ENV=nas switch               # Switch to NAS"
	@echo "  make ENV=nas rebuild              # Rebuild NAS environment"
	@echo ""
	@echo "$(CYAN)🔧 Utilities:$(NC)"
	@echo "  make ENV=<env> exec-web           # Shell into web container"
	@echo "  make ENV=<env> exec-db            # Shell into database container"
	@echo "  make ENV=<env> exec <cmd>         # Execute command in web container"
	@echo "  make ENV=<env> list-envs          # List environment variables"
	@echo ""
	@echo "$(CYAN)✨ Code Quality:$(NC)"
	@echo "  make lint                         # Check code without changes (SAFE - read-only)"
	@echo "  make lint-web                     # Check web files without changes (SAFE)"
	@echo "  make check-file-sizes             # Check for files >300 lines (detailed report)"
	@echo "  make format                       # Format & lint all code (⚠️  MODIFIES FILES)"
	@echo "  make format-python                # Format & lint Python with Ruff"
	@echo "  make format-web                   # Format & lint web (⚠️  MODIFIES FILES)"
	@echo "  make format-shell                 # Format & lint shell scripts"
	@echo "  make clean-js                     # Remove stale compiled JS from TS directories"
	@echo ""

# ============================================
# Status & Information
# ============================================
status:
	@echo "$(CYAN)📊 Environment Status:$(NC)"
	@RUNNING=$$(docker ps --format '{{.Names}}' 2>/dev/null | \
		grep -oE 'scitex-cloud-(dev|prod|nas)-' | \
		sed 's/scitex-cloud-//' | \
		sed 's/-//' | \
		sort -u | \
		tr '\n' ' ' | \
		xargs); \
	if [ -n "$$RUNNING" ]; then \
		echo "  $(CYAN)Active environment:$(NC) $$RUNNING"; \
	else \
		echo "  $(YELLOW)⚠️  No active environment$(NC)"; \
	fi
	@echo ""
	@echo "$(CYAN)🐳 Running Containers:$(NC)"
	@docker ps --format "table {{.Names}}\t{{.Status}}" 2>/dev/null | \
		grep -E "scitex-cloud-(dev|prod|nas)-" | xargs -I{} echo "  "{} || \
		echo "  $(YELLOW)No scitex-cloud containers running$(NC)"
	@echo ""
	@echo "$(CYAN)🖥️  SLURM Status:$(NC)"
	@if command -v sinfo >/dev/null 2>&1; then \
		SLURM_STATUS=$$(sinfo --noheader 2>&1); \
		if [ -n "$$SLURM_STATUS" ] && ! echo "$$SLURM_STATUS" | grep -q "error"; then \
			echo "  $(GREEN)✅ SLURM Cluster: OPERATIONAL$(NC)"; \
			sinfo --noheader 2>/dev/null | while read line; do echo "    $$line"; done; \
		else \
			echo "  $(RED)❌ SLURM Cluster: NOT RESPONDING$(NC)"; \
			echo "  $(YELLOW)💡 To start: make slurm-start$(NC)"; \
		fi; \
	else \
		echo "  $(YELLOW)⚠️  SLURM not installed$(NC)"; \
	fi
	@./scripts/check_file_sizes.sh

# ============================================
# Stop All Environments
# ============================================
stop-all:
	@echo "$(YELLOW)⬇️  Stopping all environments...$(NC)"
	@echo ""
	@for env in $(VALID_ENVS); do \
		echo "$(CYAN)Checking $$env...$(NC)"; \
		cd deployment/docker/docker_$$env && \
		if docker compose ps -q 2>/dev/null | grep -q .; then \
			echo "  $(YELLOW)Stopping $$env containers...$(NC)"; \
			$(MAKE) -f Makefile down 2>/dev/null || docker compose down 2>/dev/null || true; \
		else \
			echo "  $(GREEN)✓ $$env already stopped$(NC)"; \
		fi; \
		cd ../../..; \
	done
	@echo ""
	@echo "$(GREEN)✅ All environments stopped$(NC)"

force-stop-all:
	@echo "$(RED)⚠️  Force stopping all scitex-cloud containers...$(NC)"
	@docker ps -a --format "{{.Names}}" | grep -E "scitex-cloud-(dev|prod|nas)-" | xargs -r docker stop 2>/dev/null || true
	@docker ps -a --format "{{.Names}}" | grep -E "scitex-cloud-(dev|prod|nas)-" | xargs -r docker rm 2>/dev/null || true
	@echo "$(GREEN)✅ All containers force-stopped$(NC)"

# ============================================
# Environment Switching
# ============================================
switch: validate stop-all
	@echo ""
	@echo "$(CYAN)🔄 Switching to $(ENV) environment...$(NC)"
	@$(MAKE) --no-print-directory ENV=$(ENV) start
	@echo ""
	@echo "$(GREEN)✅ Switched to $(ENV) environment$(NC)"

# ============================================
# Service Lifecycle with Validation
# ============================================
start:
	rm -f ./logs/*.log

	@echo "$(CYAN)🚀 Starting $(ENV) environment (exclusive mode)...$(NC)"
	@echo ""
	@# Stop all other environments to ensure exclusivity
	@for env in $(VALID_ENVS); do \
		if [ "$$env" != "$(ENV)" ]; then \
			echo "$(CYAN)Checking $$env...$(NC)"; \
			cd deployment/docker/docker_$$env && \
			if docker compose ps -q 2>/dev/null | grep -q .; then \
				echo "  $(YELLOW)Stopping $$env containers...$(NC)"; \
				$(MAKE) -f Makefile down 2>/dev/null || docker compose down 2>/dev/null || true; \
			else \
				echo "  $(GREEN)✓ $$env already stopped$(NC)"; \
			fi; \
			cd ../../..; \
		fi; \
	done
	@echo ""
	@# Start the requested environment
	@echo "$(CYAN)Starting $(ENV) services...$(NC)"
	@cd $(DOCKER_DIR) && $(MAKE) -f Makefile start || (echo "$(RED)❌ Start failed. Run 'make ENV=$(ENV) start' to retry$(NC)"; exit 1)
	@echo ""
	@echo "$(GREEN)✅ $(ENV) environment is now running$(NC)"
	@$(MAKE) --no-print-directory status

restart: validate
	rm -f ./logs/*.log

	@RUNNING=$$(docker ps --format '{{.Names}}' 2>/dev/null | grep -oE 'scitex-cloud-(dev|prod|nas)-' | sed 's/scitex-cloud-//' | sed 's/-//' | sort -u); \
	if [ "$$RUNNING" != "$(ENV)" ]; then \
		echo "$(RED)❌ $(ENV) is not running ($$RUNNING is active)$(NC)"; \
		echo "$(YELLOW)   Options:$(NC)"; \
		echo "$(YELLOW)   • make env=$(ENV) start          # Start $(ENV) (stops $$RUNNING)$(NC)"; \
		echo "$(YELLOW)   • make env=$(ENV) switch         # Clean switch to $(ENV)$(NC)"; \
		echo "$(YELLOW)   • make env=$$RUNNING restart     # Restart current $$RUNNING$(NC)"; \
		exit 1; \
	fi
	@echo "$(CYAN)🔄 Restarting $(ENV) environment...$(NC)"
	@cd $(DOCKER_DIR) && $(MAKE) -f Makefile restart
	@echo "$(GREEN)✅ $(ENV) restarted$(NC)"

reload: validate
	rm -f ./logs/*.log

	@RUNNING=$$(docker ps --format '{{.Names}}' 2>/dev/null | grep -oE 'scitex-cloud-(dev|prod|nas)-' | sed 's/scitex-cloud-//' | sed 's/-//' | sort -u); \
	if [ "$$RUNNING" != "$(ENV)" ]; then \
		echo "$(RED)❌ $(ENV) is not running ($$RUNNING is active)$(NC)"; \
		echo "$(YELLOW)   Options:$(NC)"; \
		echo "$(YELLOW)   • make env=$(ENV) start          # Start $(ENV) (stops $$RUNNING)$(NC)"; \
		echo "$(YELLOW)   • make env=$(ENV) switch         # Clean switch to $(ENV)$(NC)"; \
		echo "$(YELLOW)   • make env=$$RUNNING reload      # Reload current $$RUNNING$(NC)"; \
		exit 1; \
	fi
	@echo "$(CYAN)⚡ Quick reload (no scitex reinstall)...$(NC)"
	@cd $(DOCKER_DIR) && $(MAKE) -f Makefile reload
	@echo "$(GREEN)✅ $(ENV) reloaded$(NC)"

stop: validate-docker
	@echo "$(YELLOW)⬇️  Stopping $(ENV) environment...$(NC)"
	@cd $(DOCKER_DIR) && $(MAKE) -f Makefile down
	@echo "$(GREEN)✅ $(ENV) stopped$(NC)"

down: stop

# ============================================
# Build Commands
# ============================================
build:
	@echo "$(CYAN)🏗️  Building $(ENV) images...$(NC)"
	@cd $(DOCKER_DIR) && $(MAKE) -f Makefile build
	@echo "$(GREEN)✅ Build complete for $(ENV)$(NC)"

rebuild: validate-docker
	@# NAS safety check
	@if [ "$(ENV)" = "nas" ]; then \
		echo ""; \
		echo "$(RED)⚠️  WARNING: NAS rebuild!$(NC)"; \
		echo "$(YELLOW)   This will cause downtime.$(NC)"; \
		echo ""; \
		printf "Type 'yes' to confirm: "; \
		read confirm; \
		if [ "$$confirm" != "yes" ]; then \
			echo "$(YELLOW)❌ Rebuild cancelled$(NC)"; \
			exit 1; \
		fi; \
	fi
	@echo ""
	@echo "$(CYAN)🔄 Rebuilding $(ENV) environment...$(NC)"
	@echo "  1. Stopping $(ENV)..."
	@$(MAKE) --no-print-directory ENV=$(ENV) stop
	@echo "  2. Building images..."
	@cd $(DOCKER_DIR) && $(MAKE) -f Makefile build
	@echo "  3. Starting $(ENV)..."
	@cd $(DOCKER_DIR) && $(MAKE) -f Makefile up
	@echo ""
	@echo "$(GREEN)✅ $(ENV) rebuild complete$(NC)"
	@$(MAKE) --no-print-directory validate

rebuild-no-cache: validate-docker
	@# NAS safety check
	@if [ "$(ENV)" = "nas" ]; then \
		echo ""; \
		echo "$(RED)⚠️  WARNING: NAS rebuild without cache!$(NC)"; \
		echo "$(YELLOW)   This will cause downtime and take longer.$(NC)"; \
		echo ""; \
		printf "Type 'yes' to confirm: "; \
		read confirm; \
		if [ "$$confirm" != "yes" ]; then \
			echo "$(YELLOW)❌ Rebuild cancelled$(NC)"; \
			exit 1; \
		fi; \
	fi
	@echo ""
	@echo "$(CYAN)🔄 Rebuilding $(ENV) environment (no cache)...$(NC)"
	@echo "  1. Stopping $(ENV)..."
	@$(MAKE) --no-print-directory ENV=$(ENV) stop
	@echo "  2. Building images (without cache)..."
	@cd $(DOCKER_DIR) && $(MAKE) -f Makefile build-no-cache
	@echo "  3. Starting $(ENV)..."
	@cd $(DOCKER_DIR) && $(MAKE) -f Makefile up
	@echo ""
	@echo "$(GREEN)✅ $(ENV) rebuild complete (no cache)$(NC)"
	@$(MAKE) --no-print-directory validate

setup:
	@echo "$(CYAN)🔧 Setting up $(ENV) environment...$(NC)"
	@cd $(DOCKER_DIR) && $(MAKE) -f Makefile setup
	@echo "$(GREEN)✅ $(ENV) setup complete$(NC)"

# ============================================
# Django Commands
# ============================================
migrate: validate
	@echo "$(CYAN)🔄 Running migrations ($(ENV))...$(NC)"
	@cd $(DOCKER_DIR) && $(MAKE) -f Makefile migrate

makemigrations: validate
	@echo "$(CYAN)📝 Creating migrations ($(ENV))...$(NC)"
	@cd $(DOCKER_DIR) && $(MAKE) -f Makefile makemigrations

shell: validate
	@echo "$(CYAN)🐍 Opening Django shell ($(ENV))...$(NC)"
	@cd $(DOCKER_DIR) && $(MAKE) -f Makefile shell

createsuperuser: validate
	@echo "$(CYAN)👤 Creating superuser ($(ENV))...$(NC)"
	@cd $(DOCKER_DIR) && $(MAKE) -f Makefile createsuperuser

collectstatic: validate
	@echo "$(CYAN)📦 Collecting static files ($(ENV))...$(NC)"
	@cd $(DOCKER_DIR) && $(MAKE) -f Makefile collectstatic

test: validate
	@echo "$(CYAN)🧪 Running tests ($(ENV))...$(NC)"
	@cd $(DOCKER_DIR) && $(MAKE) -f Makefile test

# E2E Testing Commands
test-e2e: validate
	@echo "$(CYAN)🎭 Running E2E tests ($(ENV))...$(NC)"
	@cd $(DOCKER_DIR) && $(MAKE) -f Makefile test-e2e

test-e2e-headed: validate
	@echo "$(CYAN)🎭 Running E2E tests with browser visible ($(ENV))...$(NC)"
	@cd $(DOCKER_DIR) && $(MAKE) -f Makefile test-e2e-headed

test-e2e-specific: validate
	@if [ -z "$(TEST)" ]; then \
		echo "$(RED)❌ TEST not specified! Use: make ENV=$(ENV) test-e2e-specific TEST=tests/e2e/test_user_creation.py$(NC)"; \
		exit 1; \
	fi
	@echo "$(CYAN)🎭 Running specific E2E test: $(TEST) ($(ENV))...$(NC)"
	@cd $(DOCKER_DIR) && $(MAKE) -f Makefile test-e2e-specific TEST=$(TEST)

# ============================================
# Database Commands
# ============================================
db-shell: validate
	@echo "$(CYAN)🗄️  Opening database shell ($(ENV))...$(NC)"
	@cd $(DOCKER_DIR) && $(MAKE) -f Makefile db-shell

db-backup: validate
	@echo "$(CYAN)💾 Backing up database ($(ENV))...$(NC)"
	@cd $(DOCKER_DIR) && $(MAKE) -f Makefile db-backup

db-reset: validate
	@if [ "$(ENV)" != "dev" ]; then \
		echo "$(RED)❌ db-reset only available in dev environment$(NC)"; \
		exit 1; \
	fi
	@echo "$(YELLOW)⚠️  Resetting database (dev only)...$(NC)"
	@cd $(DOCKER_DIR) && $(MAKE) -f Makefile db-reset

# ============================================
# Fresh Start (Complete Reset)
# ============================================
fresh-start: validate
	@if [ "$(ENV)" != "dev" ]; then \
		echo "$(RED)❌ fresh-start only available in dev environment$(NC)"; \
		echo "$(YELLOW)   This is a destructive operation meant for development$(NC)"; \
		exit 1; \
	fi
	@echo ""
	@echo "$(RED)╔═══════════════════════════════════════════════════════╗$(NC)"
	@echo "$(RED)║           ⚠️  COMPLETE FRESH START ⚠️                 ║$(NC)"
	@echo "$(RED)╚═══════════════════════════════════════════════════════╝$(NC)"
	@echo ""
	@echo "$(CYAN)📊 Current System State:$(NC)"
	@echo ""
	@# Show database info
	@USERS=$$(docker exec scitex-cloud-dev-django-1 python manage.py shell -c "from django.contrib.auth.models import User; print(User.objects.count())" 2>/dev/null | tail -1); \
	PROJECTS=$$(docker exec scitex-cloud-dev-django-1 python manage.py shell -c "from apps.project_app.models import Project; print(Project.objects.count())" 2>/dev/null | tail -1); \
	MANUSCRIPTS=$$(docker exec scitex-cloud-dev-django-1 python manage.py shell -c "from apps.writer_app.models import Manuscript; print(Manuscript.objects.count())" 2>/dev/null | tail -1); \
	REPOS=$$(docker exec scitex-cloud-dev-db-1 psql -U scitex_dev -d scitex_cloud_dev -t -c "SELECT COUNT(*) FROM repository;" 2>/dev/null | xargs); \
	DB_SIZE=$$(docker exec scitex-cloud-dev-db-1 du -sh /var/lib/postgresql/data 2>/dev/null | cut -f1); \
	GITEA_SIZE=$$(docker exec scitex-cloud-dev-gitea-1 du -sh /data 2>/dev/null | cut -f1); \
	USER_SIZE=$$(du -sh ./data/users/ 2>/dev/null | cut -f1); \
	echo "  $(YELLOW)Database:$(NC)"; \
	echo "    • Users: $$USERS"; \
	echo "    • Projects: $$PROJECTS"; \
	echo "    • Manuscripts: $$MANUSCRIPTS"; \
	echo "    • Size: $$DB_SIZE"; \
	echo ""; \
	echo "  $(YELLOW)Gitea:$(NC)"; \
	echo "    • Repositories: $$REPOS"; \
	echo "    • Size: $$GITEA_SIZE"; \
	echo ""; \
	echo "  $(YELLOW)User Files:$(NC)"; \
	echo "    • Total Size: $$USER_SIZE"; \
	echo "    • Directories: $$(ls -1 ./data/users/ 2>/dev/null | wc -l)"; \
	echo ""
	@echo "$(RED)⚠️  THIS WILL DELETE:$(NC)"
	@echo "  • All database tables (Django + Gitea)"
	@echo "  • All user directories (./data/users/*)"
	@echo "  • All Gitea repositories"
	@echo "  • All Docker volumes"
	@echo ""
	@echo "$(GREEN)✓ What's PRESERVED:$(NC)"
	@echo "  • Source code (apps/, config/, scripts/)"
	@echo "  • Docker images (no rebuild needed)"
	@echo "  • Configuration files (.env, settings)"
	@echo "  • Static files (CSS, JS, templates)"
	@echo "  • Python packages (.venv in project root)"
	@echo ""
	@echo "$(GREEN)Then it will:$(NC)"
	@echo "  • Recreate database with migrations"
	@echo "  • Initialize visitor pool (4 accounts)"
	@echo "  • Create fresh Gitea instance"
	@echo ""
	@echo "$(YELLOW)⚠️  Note: Will ask for sudo password to delete Docker-created files$(NC)"
	@echo ""
	@printf "$(YELLOW)Type 'DELETE EVERYTHING' to confirm: $(NC)"; \
	read confirm; \
	if [ "$$confirm" != "DELETE EVERYTHING" ]; then \
		echo "$(GREEN)✅ Cancelled - no changes made$(NC)"; \
		exit 0; \
	fi
	@echo ""
	@echo "$(CYAN)🔄 Starting complete fresh start...$(NC)"
	@echo ""
	@# Step 1: Stop all containers
	@echo "$(CYAN)Step 1/6: Stopping all containers...$(NC)"
	@$(MAKE) --no-print-directory stop-all
	@echo ""
	@# Step 2: Remove volumes
	@echo "$(CYAN)Step 2/6: Removing Docker volumes...$(NC)"
	@docker volume rm -f scitex-cloud-dev_postgres_data scitex-cloud-dev_gitea_data 2>/dev/null || true
	@echo "$(GREEN)✓ Volumes removed$(NC)"
	@echo ""
	@# Step 3: Clean data directories
	@echo "$(CYAN)Step 3/6: Cleaning data directories...$(NC)"
	@echo "  Removing ./data/users/* (requires sudo for Docker-created files)..."
	@if [ -d ./data/users ] && [ "$$(ls -A ./data/users 2>/dev/null)" ]; then \
		sudo rm -rf ./data/users/* || { \
			echo "$(RED)❌ Failed to remove user directories. Try: sudo rm -rf ./data/users/*$(NC)"; \
			exit 1; \
		}; \
	fi
	@echo "  Removing ./logs/*..."
	@rm -rf ./logs/*.log 2>/dev/null || true
	@echo "$(GREEN)✓ Directories cleaned$(NC)"
	@echo ""
	@# Step 4: Start containers
	@echo "$(CYAN)Step 4/6: Starting fresh containers...$(NC)"
	@$(MAKE) --no-print-directory ENV=dev start
	@echo ""
	@# Step 5: Wait for services
	@echo "$(CYAN)Step 5/6: Waiting for services to be ready...$(NC)"
	@echo "  Waiting 15 seconds for database and Gitea..."
	@sleep 15
	@echo "$(GREEN)✓ Services ready$(NC)"
	@echo ""
	@# Step 6: Initialize visitor pool
	@echo "$(CYAN)Step 6/6: Initializing visitor pool...$(NC)"
	@docker exec scitex-cloud-dev-django-1 python manage.py create_visitor_pool
	@echo ""
	@echo "$(GREEN)╔═══════════════════════════════════════════════════════╗$(NC)"
	@echo "$(GREEN)║            ✨ FRESH START COMPLETE! ✨                ║$(NC)"
	@echo "$(GREEN)╚═══════════════════════════════════════════════════════╝$(NC)"
	@echo ""
	@echo "$(CYAN)🎉 Your development environment is now clean:$(NC)"
	@echo "  • Database: Fresh with migrations applied"
	@echo "  • Visitor pool: 4 accounts ready (rotated automatically)"
	@echo "  • Gitea: Fresh instance"
	@echo "  • Files: Clean slate"
	@echo ""
	@echo "$(CYAN)📝 Next steps:$(NC)"
	@echo "  1. Create superuser: make ENV=dev createsuperuser"
	@echo "  2. Access dev server: http://localhost:8000"
	@echo "  3. Access Gitea: http://localhost:3001"
	@echo ""

# Quick fresh start without confirmation (for scripts/automation)
fresh-start-confirm: validate
	@if [ "$(ENV)" != "dev" ]; then \
		echo "$(RED)❌ fresh-start-confirm only available in dev environment$(NC)"; \
		exit 1; \
	fi
	@echo "$(YELLOW)⚠️  Running fresh start without confirmation...$(NC)"
	@$(MAKE) --no-print-directory stop-all
	@docker volume rm -f scitex-cloud-dev_postgres_data scitex-cloud-dev_gitea_data 2>/dev/null || true
	@rm -rf ./data/users/*
	@rm -rf ./logs/*.log
	@$(MAKE) --no-print-directory ENV=dev start
	@sleep 15
	@docker exec scitex-cloud-dev-django-1 python manage.py create_visitor_pool
	@echo "$(GREEN)✅ Fresh start complete$(NC)"

# ============================================
# Logs & Monitoring
# ============================================
logs: validate
	@cd $(DOCKER_DIR) && $(MAKE) -f Makefile logs

logs-web: validate
	@cd $(DOCKER_DIR) && $(MAKE) -f Makefile logs-web

logs-db: validate
	@cd $(DOCKER_DIR) && $(MAKE) -f Makefile logs-db

logs-gitea: validate
	@cd $(DOCKER_DIR) && $(MAKE) -f Makefile logs-gitea 2>/dev/null || echo "$(YELLOW)Gitea not available in $(ENV)$(NC)"

ps: validate
	@cd $(DOCKER_DIR) && $(MAKE) -f Makefile ps

# ============================================
# Shell Access
# ============================================
exec-web: validate
	@echo "$(CYAN)🐳 Opening shell in web container ($(ENV))...$(NC)"
	@cd $(DOCKER_DIR) && $(MAKE) -f Makefile exec-web

exec-db: validate
	@echo "$(CYAN)🐳 Opening shell in database container ($(ENV))...$(NC)"
	@cd $(DOCKER_DIR) && $(MAKE) -f Makefile exec-db

# Execute arbitrary command in web container
# Usage: make ENV=dev exec CMD="ls -la" or make ENV=dev exec ls -la
exec: validate
	@if [ -z "$(CMD)" ]; then \
		echo "$(YELLOW)⚠️  No CMD specified, using remaining args: $(filter-out $@,$(MAKECMDGOALS))$(NC)"; \
		cd $(DOCKER_DIR) && docker compose exec web $(filter-out $@,$(MAKECMDGOALS)); \
	else \
		echo "$(CYAN)🐳 Executing command in web container ($(ENV)): $(CMD)$(NC)"; \
		cd $(DOCKER_DIR) && docker compose exec web $(CMD); \
	fi

# Catch-all rule to prevent "No rule to make target" errors when using exec
%:
	@:

exec-gitea: validate
	@echo "$(CYAN)🐳 Opening shell in Gitea container ($(ENV))...$(NC)"
	@cd $(DOCKER_DIR) && $(MAKE) -f Makefile exec-gitea 2>/dev/null || echo "$(YELLOW)Gitea not available in $(ENV)$(NC)"

list-envs: validate
	@echo "$(CYAN)🔍 Environment variables in $(ENV):$(NC)"
	@docker exec scitex-cloud-$(ENV)-web-1 env | sort

# ============================================
# Dev-Only Commands
# ============================================
gitea-token:
ifeq ($(ENV),dev)
	@echo "$(CYAN)🔑 Setting up Gitea token (dev)...$(NC)"
	cd $(DOCKER_DIR) && $(MAKE) -f Makefile gitea-token
else
	@echo "$(YELLOW)❌ gitea-token only available in dev environment$(NC)"
	@exit 1
endif

recreate-testuser:
ifeq ($(ENV),dev)
	@echo "$(CYAN)👤 Recreating test user (dev)...$(NC)"
	cd $(DOCKER_DIR) && $(MAKE) -f Makefile recreate-testuser
else
	@echo "$(YELLOW)❌ recreate-testuser only available in dev environment$(NC)"
	@exit 1
endif

# ============================================
# Health Checks
# ============================================
verify-health: validate
	@if [ "$(ENV)" = "dev" ]; then \
		echo "$(YELLOW)❌ verify-health only available in nas$(NC)"; \
		exit 1; \
	fi
	@cd $(DOCKER_DIR) && $(MAKE) -f Makefile verify-health

# ============================================
# Utilities
# ============================================
clean-python:
	@cd $(DOCKER_DIR) && $(MAKE) -f Makefile clean-python

clean-js:
	@echo "$(CYAN)🧹 Cleaning stale JS files from TypeScript directories...$(NC)"
	@./scripts/maintenance/clean_stale_js.sh
	@echo "$(GREEN)✅ Done! Run 'make env=dev restart' to apply changes$(NC)"

# ============================================
# Code Quality (Format + Lint)
# ============================================
format: format-python format-web format-shell
	@echo ""
	@echo "$(GREEN)✅ All formatting and linting complete!$(NC)"

format-python:
	@echo "$(CYAN)🐍 Formatting and linting Python code with Ruff...$(NC)"
	@if command -v ruff >/dev/null 2>&1; then \
		ruff format apps/ --respect-gitignore --quiet || echo "$(YELLOW)⚠️  Ruff formatting completed with warnings$(NC)"; \
		ruff check --fix apps/ --exclude migrations --respect-gitignore --quiet || echo "$(RED)❌ Ruff found errors$(NC)"; \
		echo "$(GREEN)✅ Python formatting and linting complete!$(NC)"; \
	else \
		echo "$(RED)❌ Ruff not found. Install with: pip install ruff$(NC)"; \
		exit 1; \
	fi

format-web:
	@echo ""
	@echo "$(RED)⚠️  WARNING: This command will MODIFY your files!$(NC)"
	@echo "$(YELLOW)   • djLint will reformat Django templates$(NC)"
	@echo "$(YELLOW)   • Prettier will reformat JS/TS/CSS$(NC)"
	@echo "$(YELLOW)   • ESLint --fix will auto-fix code violations$(NC)"
	@echo ""
	@echo "$(CYAN)💡 For read-only checking (SAFE): make lint-web$(NC)"
	@echo ""
	@printf "$(YELLOW)Type 'yes' to continue with formatting: $(NC)"; \
	read confirm; \
	if [ "$$confirm" != "yes" ]; then \
		echo "$(GREEN)✅ Cancelled - no changes made$(NC)"; \
		exit 0; \
	fi
	@echo ""
	@echo "$(CYAN)✨ Formatting and linting web files...$(NC)"
	@echo "$(CYAN)📝 Formatting Django templates with djLint...$(NC)"
	@if command -v djlint >/dev/null 2>&1; then \
		djlint --reformat --quiet \
			apps/ templates/ \
			2>&1 || echo "$(YELLOW)⚠️  djLint formatting completed with warnings$(NC)"; \
		echo "$(GREEN)✅ Django template formatting complete!$(NC)"; \
	else \
		echo "$(YELLOW)⚠️  djLint not found. Install with: pip install djlint$(NC)"; \
		echo "$(YELLOW)   Skipping Django template formatting...$(NC)"; \
	fi
	@echo "$(CYAN)💅 Formatting JS/TS/CSS with Prettier...$(NC)"
	@if command -v prettier >/dev/null 2>&1; then \
		prettier --write \
			"apps/**/*.{ts,js,css}" \
			"static/**/*.{ts,js,css}" \
			--ignore-path .gitignore \
			--log-level warn \
			2>&1 || echo "$(YELLOW)⚠️  Prettier formatting completed with warnings$(NC)"; \
		echo "$(GREEN)✅ Prettier formatting complete!$(NC)"; \
	else \
		echo "$(RED)❌ Prettier not found. Install with: npm install -g prettier$(NC)"; \
		exit 1; \
	fi
	@echo "$(CYAN)🔍 Linting TS/JS with ESLint --fix...$(NC)"
	@if command -v eslint >/dev/null 2>&1; then \
		eslint --fix \
			"apps/**/*.{ts,js}" \
			"static/**/*.{ts,js}" \
			--ignore-path .gitignore \
			--quiet \
			2>&1 || echo "$(RED)❌ ESLint found errors$(NC)"; \
		echo "$(GREEN)✅ ESLint linting complete!$(NC)"; \
	else \
		echo "$(RED)❌ ESLint not found. Install with: npm install -g eslint$(NC)"; \
		exit 1; \
	fi

format-shell:
	@echo "$(CYAN)🐚 Formatting and linting shell scripts...$(NC)"
	@if command -v shfmt >/dev/null 2>&1; then \
		find scripts/ deployment/ apps/ -name "*.sh" \
			! -path "*/externals/*" \
			! -path "*/node_modules/*" \
			! -path "*/.venv/*" \
			-exec shfmt -w -i 4 -bn -ci -sr {} + \
			2>&1 || echo "$(YELLOW)⚠️  shfmt formatting completed with warnings$(NC)"; \
		echo "$(GREEN)✅ Shell formatting complete!$(NC)"; \
	else \
		echo "$(YELLOW)⚠️  shfmt not found. Install with: go install mvdan.cc/sh/v3/cmd/shfmt@latest$(NC)"; \
		echo "$(YELLOW)   Skipping shell formatting...$(NC)"; \
	fi
	@if command -v shellcheck >/dev/null 2>&1; then \
		find scripts/ deployment/ apps/ -name "*.sh" \
			! -path "*/externals/*" \
			! -path "*/node_modules/*" \
			! -path "*/.venv/*" \
			-exec shellcheck --severity=error {} + \
			2>&1 || echo "$(RED)❌ ShellCheck found errors$(NC)"; \
		echo "$(GREEN)✅ Shell linting complete!$(NC)"; \
	else \
		echo "$(YELLOW)⚠️  shellcheck not found. Install with: sudo apt-get install shellcheck$(NC)"; \
		echo "$(YELLOW)   Skipping shell linting...$(NC)"; \
	fi

# ============================================
# Linting (Read-Only - SAFE)
# ============================================
lint: lint-web
	@echo ""
	@echo "$(GREEN)✅ All linting checks complete (no files modified)!$(NC)"

lint-web:
	@echo "$(GREEN)✅ SAFE MODE: Checking files without making changes$(NC)"
	@echo ""
	@echo "$(CYAN)🔍 Checking TS/JS with ESLint (read-only)...$(NC)"
	@if command -v eslint >/dev/null 2>&1; then \
		npx eslint \
			"apps/**/*.{ts,js}" \
			"static/**/*.{ts,js}" \
			2>&1 | head -100 || true; \
		echo ""; \
		echo "$(GREEN)✅ ESLint check complete!$(NC)"; \
		echo "$(CYAN)💡 To auto-fix issues: make format-web$(NC)"; \
	else \
		echo "$(RED)❌ ESLint not found. Install with: npm install -g eslint$(NC)"; \
		exit 1; \
	fi
	@echo ""
	@echo "$(CYAN)💅 Checking JS/TS/CSS with Prettier (read-only)...$(NC)"
	@if command -v prettier >/dev/null 2>&1; then \
		prettier --check \
			"apps/**/*.{ts,js,css}" \
			"static/**/*.{ts,js,css}" \
			--ignore-path .gitignore \
			--log-level warn \
			2>&1 | head -50 || true; \
		echo ""; \
		echo "$(GREEN)✅ Prettier check complete!$(NC)"; \
	else \
		echo "$(RED)❌ Prettier not found. Install with: npm install -g prettier$(NC)"; \
		exit 1; \
	fi

# ============================================
# File Size Checks
# ============================================
check-file-sizes:
	@echo "$(CYAN)📏 Checking file sizes (>300 line threshold)...$(NC)"
	@./scripts/check_file_sizes.sh --verbose

# ============================================
# Info
# ============================================
info:
	@echo "Specified environment: $(ENV)"
	@echo "Running environments: $$(docker ps --format '{{.Names}}' 2>/dev/null | grep -oE 'scitex-cloud-(dev|prod|nas)-' | sed 's/scitex-cloud-//' | sed 's/-//' | sort -u | tr '\n' ' ')"
	@echo "Container directory: $(DOCKER_DIR)"
	@echo "Makefile: $(MAKEFILE)"

# ============================================
# SLURM Management
# ============================================
slurm-start:
	@echo "$(CYAN)🚀 Starting SLURM services...$(NC)"
	@echo "  Starting munge..."
	@sudo systemctl start munge 2>&1 || sudo service munge start 2>&1 || echo "$(YELLOW)  munge may already be running$(NC)"
	@echo "  Starting slurmctld..."
	@sudo systemctl start slurmctld 2>&1 || sudo service slurmctld start 2>&1 || echo "$(RED)  Failed to start slurmctld$(NC)"
	@echo "  Starting slurmd..."
	@sudo systemctl start slurmd 2>&1 || sudo service slurmd start 2>&1 || echo "$(RED)  Failed to start slurmd$(NC)"
	@sleep 2
	@$(MAKE) slurm-status

slurm-stop:
	@echo "$(YELLOW)⏹️  Stopping SLURM services...$(NC)"
	@sudo systemctl stop slurmd slurmctld 2>/dev/null || \
		(sudo service slurmd stop && sudo service slurmctld stop) 2>/dev/null || \
		echo "$(RED)❌ Failed to stop SLURM$(NC)"
	@$(MAKE) slurm-status

slurm-restart:
	@echo "$(CYAN)🔄 Restarting SLURM services...$(NC)"
	@$(MAKE) slurm-stop
	@sleep 1
	@$(MAKE) slurm-start

slurm-status:
	@echo "$(CYAN)🖥️  SLURM Status:$(NC)"
	@if command -v sinfo >/dev/null 2>&1; then \
		SLURM_STATUS=$$(sinfo --noheader 2>&1); \
		if [ -n "$$SLURM_STATUS" ] && ! echo "$$SLURM_STATUS" | grep -q "error"; then \
			echo "  $(GREEN)✅ SLURM Cluster: OPERATIONAL$(NC)"; \
			echo ""; \
			echo "  Partitions:"; \
			sinfo 2>/dev/null | head -10 | while read line; do echo "    $$line"; done; \
			echo ""; \
			echo "  Jobs:"; \
			squeue 2>/dev/null | head -10 | while read line; do echo "    $$line"; done; \
		else \
			echo "  $(RED)❌ SLURM Cluster: NOT RESPONDING$(NC)"; \
			echo "  $(YELLOW)💡 To fix: make slurm-fix$(NC)"; \
		fi; \
	else \
		echo "  $(YELLOW)⚠️  SLURM not installed$(NC)"; \
	fi

slurm-fix:
	@echo "$(CYAN)🔧 Fixing SLURM (requires sudo)...$(NC)"
	@sudo ./deployment/slurm/scripts/07_fix_munge_auth.sh
	@$(MAKE) slurm-status

slurm-resume:
	@echo "$(CYAN)🔄 Resuming SLURM nodes...$(NC)"
	@HOSTNAME=$$(hostname); \
	echo "  Resuming node: $$HOSTNAME"; \
	sudo scontrol update nodename=$$HOSTNAME state=resume; \
	sleep 2
	@$(MAKE) slurm-status

slurm-reset:
	@echo "$(RED)⚠️  This will clear ALL SLURM jobs and reset state!$(NC)"
	@read -p "Are you sure? (y/N) " confirm && [ "$$confirm" = "y" ] || exit 1
	@sudo ./deployment/slurm/scripts/08_reset_slurm_state.sh
	@$(MAKE) slurm-status

# EOF
