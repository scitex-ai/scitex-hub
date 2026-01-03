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

# Use bash for proper echo -e support (dash/sh don't support -e flag)
SHELL := /bin/bash

.PHONY: \
	help \
	status \
	status-live \
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
	build-no-cache \
	rebuild \
	rebuild-no-cache \
	setup \
	test \
	test-e2e \
	test-e2e-headed \
	test-e2e-specific \
	sync-tests \
	sync-tests-move \
	sync-ts-tests \
	sync-ts-tests-move \
	setup-vitest \
	test-ts \
	test-ts-watch \
	test-ts-ui \
	test-ts-coverage \
	setup-pytest \
	setup-testing \
	test-unit \
	test-db \
	test-api \
	test-ui \
	test-ui-headed \
	test-python \
	test-all \
	test-status \
	clean-python \
	clean-js \
	format \
	format-python \
	format-web \
	format-shell \
	lint \
	lint-web \
	check-file-sizes \
	check-host \
	ensure-executable \
	info \
	regenerate-gallery

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
    ifneq ($(filter-out help status validate-docker stop-all force-stop-all format format-python format-web format-shell lint lint-web check-file-sizes check-assets check-host ensure-executable slurm-start slurm-stop slurm-restart slurm-status slurm-fix slurm-resume slurm-reset crossref-status crossref-check crossref-rebuild-check crossref-next-steps crossref-create-title-index crossref-create-author-index info regenerate-gallery sync-tests sync-tests-move sync-ts-tests sync-ts-tests-move setup-vitest test-ts test-ts-watch test-ts-ui test-ts-coverage setup-pytest setup-testing test-unit test-db test-api test-ui test-ui-headed test-python test-all test-status,$(MAKECMDGOALS)),)
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
	@echo -e "$(CYAN)🔍 Checking for container conflicts...$(NC)"
	@RUNNING=$$(docker ps --format '{{.Names}}' 2>/dev/null | grep -oE 'scitex-cloud-(dev|prod|nas)-' | sed 's/scitex-cloud-//' | sed 's/-//' | sort -u); \
	COUNT=$$(echo "$$RUNNING" | wc -w); \
	if [ $$COUNT -gt 1 ]; then \
		echo -e "$(RED)❌ CONFLICT: Multiple environments running:$(NC)"; \
		for env in $$RUNNING; do \
			echo "  - $$env"; \
		done; \
		echo -e "$(YELLOW)   Run 'make stop-all' to clean up$(NC)"; \
		exit 1; \
	fi; \
	if [ $$COUNT -eq 0 ]; then \
		echo -e "$(GREEN)✅ No containers running$(NC)"; \
	else \
		echo -e "$(GREEN)✅ Only $$RUNNING is running$(NC)"; \
	fi

# Validation alias
validate: validate-docker

# ============================================
# Help
# ============================================
help:
	@echo -e ""
	@echo -e "$(GREEN)╔═══════════════════════════════════════════════════════╗$(NC)"
	@echo -e "$(GREEN)║      SciTeX Cloud - Environment Orchestrator          ║$(NC)"
	@echo -e "$(GREEN)╚═══════════════════════════════════════════════════════╝$(NC)"
	@echo -e ""
	@$(MAKE) --no-print-directory status
	@echo -e ""
	@echo -e "$(CYAN)📋 Core Commands:$(NC)"
	@echo -e "  make status                       # Show active environment"
	@echo -e "  make validate                     # Validate state consistency"
	@echo -e "  make ENV=<env> start              # Start environment (stops others)"
	@echo -e "  make ENV=<env> switch             # Switch environment cleanly"
	@echo -e "  make ENV=<env> stop               # Stop specific environment"
	@echo -e "  make stop-all                     # Stop all environments"
	@echo -e ""
	@echo -e "$(CYAN)🔧 Build & Deploy:$(NC)"
	@echo -e "  make ENV=<env> build              # Build images"
	@echo -e "  make ENV=<env> rebuild            # Rebuild (stops, builds, starts)"
	@echo -e "  make ENV=<env> rebuild-no-cache   # Rebuild without cache (for dependency fixes)"
	@echo -e "  make ENV=<env> setup              # Full setup (build + migrate)"
	@echo -e ""
	@echo -e "$(CYAN)🐍 Django:$(NC)"
	@echo -e "  make ENV=<env> migrate            # Run migrations"
	@echo -e "  make ENV=<env> shell              # Django shell"
	@echo -e "  make ENV=<env> collectstatic      # Collect static files"
	@echo -e ""
	@echo -e "$(CYAN)🔄 Reset & Fresh Start:$(NC)"
	@echo -e "  make ENV=dev fresh-start          # Complete reset: DB + Gitea + Files (dev only)"
	@echo -e "  make ENV=dev fresh-start-confirm  # Skip confirmation (use with caution)"
	@echo -e ""
	@echo -e "$(CYAN)📊 Monitoring:$(NC)"
	@echo -e "  make ENV=<env> logs               # View logs"
	@echo -e "  make ENV=<env> ps                 # Container status"
	@echo -e ""
	@echo -e "$(CYAN)📊 CrossRef Database:$(NC)"
	@echo -e "  make crossref-status              # Check citations rebuild progress"
	@echo -e "  make crossref-check               # Check if rebuild is complete"
	@echo -e "  make crossref-next-steps          # Show next optimization steps"
	@echo -e ""
	@echo -e "$(CYAN)💡 Examples:$(NC)"
	@echo -e "  make status                       # Check what's running"
	@echo -e "  make ENV=dev start                # Start development"
	@echo -e "  make ENV=nas switch               # Switch to NAS"
	@echo -e "  make ENV=nas rebuild              # Rebuild NAS environment"
	@echo -e "  make crossref-status              # Check CrossRef rebuild"
	@echo -e ""
	@echo -e "$(CYAN)🔧 Utilities:$(NC)"
	@echo -e "  make ENV=<env> exec-web           # Shell into web container"
	@echo -e "  make ENV=<env> exec-db            # Shell into database container"
	@echo -e "  make ENV=<env> exec <cmd>         # Execute command in web container"
	@echo -e "  make ENV=<env> list-envs          # List environment variables"
	@echo -e "  make ensure-executable            # Ensure all scripts have +x permission"
	@echo -e "  make sync-tests                   # Sync Python test stubs with apps/"
	@echo -e "  make sync-tests-move              # Sync Python tests, move stale files"
	@echo -e "  make sync-ts-tests                # Sync TypeScript test stubs"
	@echo -e "  make sync-ts-tests-move           # Sync TS tests, move stale files"
	@echo -e ""
	@echo -e "$(CYAN)🧪 Testing:$(NC)"
	@echo -e "  make setup-testing                # Install all test dependencies"
	@echo -e "  make setup-pytest                 # Install Python testing (pytest + playwright)"
	@echo -e "  make setup-vitest                 # Install TypeScript testing (vitest)"
	@echo -e ""
	@echo -e "$(CYAN)🐍 Python Testing:$(NC)"
	@echo -e "  make test-unit                    # Run unit tests (no DB)"
	@echo -e "  make test-db                      # Run database tests"
	@echo -e "  make test-api                     # Run API endpoint tests"
	@echo -e "  make test-ui                      # Run UI tests (headless)"
	@echo -e "  make test-ui-headed               # Run UI tests (visible browser)"
	@echo -e "  make test-python                  # Run all Python tests"
	@echo -e ""
	@echo -e "$(CYAN)📘 TypeScript Testing:$(NC)"
	@echo -e "  make test-ts                      # Run TypeScript tests (single run)"
	@echo -e "  make test-ts-watch                # Run tests in watch mode"
	@echo -e "  make test-ts-ui                   # Open Vitest visual UI"
	@echo -e "  make test-ts-coverage             # Run tests with coverage report"
	@echo -e ""
	@echo -e "$(CYAN)🚀 All Tests:$(NC)"
	@echo -e "  make test-all                     # Run all tests (Python + TypeScript)"
	@echo -e "  make test-status                  # Show test infrastructure status"
	@echo -e ""
	@echo -e "$(CYAN)✨ Code Quality:$(NC)"
	@echo -e "  make lint                         # Check code without changes (SAFE - read-only)"
	@echo -e "  make lint-web                     # Check web files without changes (SAFE)"
	@echo -e "  make check-file-sizes             # Check for files >300 lines (detailed report)"
	@echo -e "  make check-host                   # Check host requirements (users, SLURM)"
	@echo -e "  make format                       # Format & lint all code (⚠️  MODIFIES FILES)"
	@echo -e "  make format-python                # Format & lint Python with Ruff"
	@echo -e "  make format-web                   # Format & lint web (⚠️  MODIFIES FILES)"
	@echo -e "  make format-shell                 # Format & lint shell scripts"
	@echo -e "  make clean-js                     # Remove stale compiled JS from TS directories"
	@echo -e ""

# ============================================
# Status & Information
# ============================================
status:
	@./deployment/host-setup/checks/check-status.sh

# Live status with spinners and animations
status-live:
	@./scripts/maintenance/check_status_live.sh $(ENV)
	@echo -e ""
	@./scripts/maintenance/check_file_sizes.sh

# ============================================
# Stop All Environments
# ============================================
stop-all:
	@echo -e "$(YELLOW)⬇️  Stopping all environments...$(NC)"
	@echo -e ""
	@for env in $(VALID_ENVS); do \
		echo -e "$(CYAN)Checking $$env...$(NC)"; \
		cd deployment/docker/docker_$$env && \
		if docker compose ps -q 2>/dev/null | grep -q .; then \
			echo -e "  $(YELLOW)Stopping $$env containers...$(NC)"; \
			$(MAKE) -f Makefile down 2>/dev/null || docker compose down 2>/dev/null || true; \
		else \
			echo -e "  $(GREEN)✓ $$env already stopped$(NC)"; \
		fi; \
		cd ../../..; \
	done
	@echo -e ""
	@echo -e "$(GREEN)✅ All environments stopped$(NC)"

force-stop-all:
	@echo -e "$(RED)⚠️  Force stopping all scitex-cloud containers...$(NC)"
	@docker ps -a --format "{{.Names}}" | grep -E "scitex-cloud-(dev|prod|nas)-" | xargs -r docker stop 2>/dev/null || true
	@docker ps -a --format "{{.Names}}" | grep -E "scitex-cloud-(dev|prod|nas)-" | xargs -r docker rm 2>/dev/null || true
	@echo -e "$(GREEN)✅ All containers force-stopped$(NC)"

# ============================================
# Environment Switching
# ============================================
switch: validate stop-all
	@echo -e ""
	@echo -e "$(CYAN)🔄 Switching to $(ENV) environment...$(NC)"
	@$(MAKE) --no-print-directory ENV=$(ENV) start
	@echo -e ""
	@echo -e "$(GREEN)✅ Switched to $(ENV) environment$(NC)"

# ============================================
# Service Lifecycle with Validation
# ============================================
start:
	rm -f ./logs/*.log

	@echo -e "$(CYAN)🚀 Starting $(ENV) environment (exclusive mode)...$(NC)"
	@echo -e ""
	@# Check host requirements for NAS environment
	@if [ "$(ENV)" = "nas" ]; then \
		echo -e "$(CYAN)Checking NAS host requirements...$(NC)"; \
		echo ""; \
		if ! deployment/host-setup/checks/check-users.sh; then \
			echo ""; \
			echo -e "$(RED)❌ Host requirements not met!$(NC)"; \
			echo -e "$(YELLOW)   Run: sudo deployment/host-setup/scripts/create-scitex-user.sh$(NC)"; \
			exit 1; \
		fi; \
		if ! deployment/host-setup/checks/check-slurm.sh; then \
			echo ""; \
			echo -e "$(RED)❌ SLURM configuration issues detected!$(NC)"; \
			echo -e "$(YELLOW)   Fix SLURM issues before starting$(NC)"; \
			exit 1; \
		fi; \
		echo -e "$(GREEN)✓ Host requirements OK$(NC)"; \
		echo ""; \
		echo -e "$(CYAN)Checking SLURM paths (/opt/scitex)...$(NC)"; \
		if [ -f "/opt/scitex/singularity/scitex-user-workspace.sif" ]; then \
			echo -e "$(GREEN)✓ SLURM paths configured$(NC)"; \
		else \
			echo -e "$(YELLOW)⚠️  SLURM paths not configured (terminal will fail)$(NC)"; \
			echo -e "$(YELLOW)   Setup: sudo ./deployment/host-setup/scripts/setup-slurm-paths.sh$(NC)"; \
		fi; \
		echo ""; \
	fi
	@# Stop all other environments to ensure exclusivity
	@for env in $(VALID_ENVS); do \
		if [ "$$env" != "$(ENV)" ]; then \
			echo -e "$(CYAN)Checking $$env...$(NC)"; \
			cd deployment/docker/docker_$$env && \
			if docker compose ps -q 2>/dev/null | grep -q .; then \
				echo -e "  $(YELLOW)Stopping $$env containers...$(NC)"; \
				$(MAKE) -f Makefile down 2>/dev/null || docker compose down 2>/dev/null || true; \
			else \
				echo -e "  $(GREEN)✓ $$env already stopped$(NC)"; \
			fi; \
			cd ../../..; \
		fi; \
	done
	@echo -e ""
	@# Start the requested environment
	@echo -e "$(CYAN)Starting $(ENV) services...$(NC)"
	@cd $(DOCKER_DIR) && $(MAKE) -f Makefile start || (echo "$(RED)❌ Start failed. Run 'make ENV=$(ENV) start' to retry$(NC)"; exit 1)
	@echo -e ""
	@echo -e "$(GREEN)✅ $(ENV) environment is now running$(NC)"
	@$(MAKE) --no-print-directory status

restart: validate
	@# Clear logs - use docker exec for root-owned files (includes rotated logs like *.log.1)
	@docker exec scitex-cloud-$(ENV)-web-1 sh -c 'rm -f /app/logs/*.log /app/logs/*.log.[0-9]*' 2>/dev/null || true
	@rm -f ./logs/*.log ./logs/*.log.[0-9]* 2>/dev/null || true

	@RUNNING=$$(docker ps --format '{{.Names}}' 2>/dev/null | grep -oE 'scitex-cloud-(dev|prod|nas)-' | sed 's/scitex-cloud-//' | sed 's/-//' | sort -u); \
	if [ "$$RUNNING" != "$(ENV)" ]; then \
		echo -e "$(RED)❌ $(ENV) is not running ($$RUNNING is active)$(NC)"; \
		echo -e "$(YELLOW)   Options:$(NC)"; \
		echo -e "$(YELLOW)   • make env=$(ENV) start          # Start $(ENV) (stops $$RUNNING)$(NC)"; \
		echo -e "$(YELLOW)   • make env=$(ENV) switch         # Clean switch to $(ENV)$(NC)"; \
		echo -e "$(YELLOW)   • make env=$$RUNNING restart     # Restart current $$RUNNING$(NC)"; \
		exit 1; \
	fi
	@echo -e "$(CYAN)🔄 Restarting $(ENV) environment...$(NC)"
	@cd $(DOCKER_DIR) && $(MAKE) -f Makefile restart
	@echo -e "$(GREEN)✅ $(ENV) restarted$(NC)"

reload: validate
	@# Clear logs - use docker exec for root-owned files (includes rotated logs like *.log.1)
	@docker exec scitex-cloud-$(ENV)-web-1 sh -c 'rm -f /app/logs/*.log /app/logs/*.log.[0-9]*' 2>/dev/null || true
	@rm -f ./logs/*.log ./logs/*.log.[0-9]* 2>/dev/null || true

	@RUNNING=$$(docker ps --format '{{.Names}}' 2>/dev/null | grep -oE 'scitex-cloud-(dev|prod|nas)-' | sed 's/scitex-cloud-//' | sed 's/-//' | sort -u); \
	if [ "$$RUNNING" != "$(ENV)" ]; then \
		echo -e "$(RED)❌ $(ENV) is not running ($$RUNNING is active)$(NC)"; \
		echo -e "$(YELLOW)   Options:$(NC)"; \
		echo -e "$(YELLOW)   • make env=$(ENV) start          # Start $(ENV) (stops $$RUNNING)$(NC)"; \
		echo -e "$(YELLOW)   • make env=$(ENV) switch         # Clean switch to $(ENV)$(NC)"; \
		echo -e "$(YELLOW)   • make env=$$RUNNING reload      # Reload current $$RUNNING$(NC)"; \
		exit 1; \
	fi
	@echo -e "$(CYAN)⚡ Quick reload (no scitex reinstall)...$(NC)"
	@cd $(DOCKER_DIR) && $(MAKE) -f Makefile reload
	@echo -e "$(GREEN)✅ $(ENV) reloaded$(NC)"

stop: validate-docker
	@echo -e "$(YELLOW)⬇️  Stopping $(ENV) environment...$(NC)"
	@cd $(DOCKER_DIR) && $(MAKE) -f Makefile down
	@echo -e "$(GREEN)✅ $(ENV) stopped$(NC)"

down: stop

# ============================================
# Build Commands
# ============================================
build:
	@echo -e "$(CYAN)🏗️  Building $(ENV) images...$(NC)"
	@# Check host requirements for NAS (informational)
	@if [ "$(ENV)" = "nas" ]; then \
		echo ""; \
		echo -e "$(CYAN)Checking NAS host requirements...$(NC)"; \
		echo ""; \
		deployment/host-setup/checks/check-users.sh || true; \
		echo ""; \
		deployment/host-setup/checks/check-slurm.sh || true; \
		echo ""; \
	fi
	@cd $(DOCKER_DIR) && $(MAKE) -f Makefile build
	@echo -e "$(GREEN)✅ Build complete for $(ENV)$(NC)"

build-no-cache:
	@echo -e "$(CYAN)🏗️  Building $(ENV) images (no cache)...$(NC)"
	@echo -e "$(YELLOW)⚠️  This will rebuild from scratch and may take longer.$(NC)"
	@# Check host requirements for NAS (informational)
	@if [ "$(ENV)" = "nas" ]; then \
		echo ""; \
		echo -e "$(CYAN)Checking NAS host requirements...$(NC)"; \
		echo ""; \
		deployment/host-setup/checks/check-users.sh || true; \
		echo ""; \
		deployment/host-setup/checks/check-slurm.sh || true; \
		echo ""; \
	fi
	@cd $(DOCKER_DIR) && $(MAKE) -f Makefile build-no-cache
	@echo -e "$(GREEN)✅ Build complete for $(ENV)$(NC)"

rebuild: validate-docker
	@# NAS safety check
	@if [ "$(ENV)" = "nas" ]; then \
		echo ""; \
		echo -e "$(RED)⚠️  WARNING: NAS rebuild!$(NC)"; \
		echo -e "$(YELLOW)   This will cause downtime.$(NC)"; \
		echo ""; \
		printf "Type 'yes' to confirm: "; \
		read confirm; \
		if [ "$$confirm" != "yes" ]; then \
			echo -e "$(YELLOW)❌ Rebuild cancelled$(NC)"; \
			exit 1; \
		fi; \
	fi
	@echo -e ""
	@echo -e "$(CYAN)🔄 Rebuilding $(ENV) environment...$(NC)"
	@echo -e "  1. Stopping $(ENV)..."
	@$(MAKE) --no-print-directory ENV=$(ENV) stop
	@echo -e "  2. Building images..."
	@cd $(DOCKER_DIR) && $(MAKE) -f Makefile build
	@echo -e "  3. Starting $(ENV)..."
	@cd $(DOCKER_DIR) && $(MAKE) -f Makefile up
	@echo -e ""
	@echo -e "$(GREEN)✅ $(ENV) rebuild complete$(NC)"
	@$(MAKE) --no-print-directory validate

rebuild-no-cache: validate-docker
	@# NAS safety check
	@if [ "$(ENV)" = "nas" ]; then \
		echo ""; \
		echo -e "$(RED)⚠️  WARNING: NAS rebuild without cache!$(NC)"; \
		echo -e "$(YELLOW)   This will cause downtime and take longer.$(NC)"; \
		echo ""; \
		printf "Type 'yes' to confirm: "; \
		read confirm; \
		if [ "$$confirm" != "yes" ]; then \
			echo -e "$(YELLOW)❌ Rebuild cancelled$(NC)"; \
			exit 1; \
		fi; \
	fi
	@echo -e ""
	@echo -e "$(CYAN)🔄 Rebuilding $(ENV) environment (no cache)...$(NC)"
	@echo -e "  1. Stopping $(ENV)..."
	@$(MAKE) --no-print-directory ENV=$(ENV) stop
	@echo -e "  2. Building images (without cache)..."
	@cd $(DOCKER_DIR) && $(MAKE) -f Makefile build-no-cache
	@echo -e "  3. Starting $(ENV)..."
	@cd $(DOCKER_DIR) && $(MAKE) -f Makefile up
	@echo -e ""
	@echo -e "$(GREEN)✅ $(ENV) rebuild complete (no cache)$(NC)"
	@$(MAKE) --no-print-directory validate

setup:
	@echo -e "$(CYAN)🔧 Setting up $(ENV) environment...$(NC)"
	@cd $(DOCKER_DIR) && $(MAKE) -f Makefile setup
	@echo -e "$(GREEN)✅ $(ENV) setup complete$(NC)"

# ============================================
# Django Commands
# ============================================
migrate: validate
	@echo -e "$(CYAN)🔄 Running migrations ($(ENV))...$(NC)"
	@cd $(DOCKER_DIR) && $(MAKE) -f Makefile migrate

makemigrations: validate
	@echo -e "$(CYAN)📝 Creating migrations ($(ENV))...$(NC)"
	@cd $(DOCKER_DIR) && $(MAKE) -f Makefile makemigrations

shell: validate
	@echo -e "$(CYAN)🐍 Opening Django shell ($(ENV))...$(NC)"
	@cd $(DOCKER_DIR) && $(MAKE) -f Makefile shell

createsuperuser: validate
	@echo -e "$(CYAN)👤 Creating superuser ($(ENV))...$(NC)"
	@cd $(DOCKER_DIR) && $(MAKE) -f Makefile createsuperuser

collectstatic: validate
	@echo -e "$(CYAN)📦 Collecting static files ($(ENV))...$(NC)"
	@cd $(DOCKER_DIR) && $(MAKE) -f Makefile collectstatic

test: validate
	@echo -e "$(CYAN)🧪 Running tests ($(ENV))...$(NC)"
	@cd $(DOCKER_DIR) && $(MAKE) -f Makefile test

# E2E Testing Commands
test-e2e: validate
	@echo -e "$(CYAN)🎭 Running E2E tests ($(ENV))...$(NC)"
	@cd $(DOCKER_DIR) && $(MAKE) -f Makefile test-e2e

test-e2e-headed: validate
	@echo -e "$(CYAN)🎭 Running E2E tests with browser visible ($(ENV))...$(NC)"
	@cd $(DOCKER_DIR) && $(MAKE) -f Makefile test-e2e-headed

test-e2e-specific: validate
	@if [ -z "$(TEST)" ]; then \
		echo -e "$(RED)❌ TEST not specified! Use: make ENV=$(ENV) test-e2e-specific TEST=tests/e2e/test_user_creation.py$(NC)"; \
		exit 1; \
	fi
	@echo -e "$(CYAN)🎭 Running specific E2E test: $(TEST) ($(ENV))...$(NC)"
	@cd $(DOCKER_DIR) && $(MAKE) -f Makefile test-e2e-specific TEST=$(TEST)

# Test Synchronization (mirrors apps/ -> tests/apps/)
sync-tests:
	@echo -e "$(CYAN)🔄 Synchronizing test files with source...$(NC)"
	@./scripts/testing/sync_tests_with_source.sh $(if $(MOVE),-m,)
	@echo -e "$(GREEN)✅ Test sync complete$(NC)"

sync-tests-move:
	@echo -e "$(CYAN)🔄 Synchronizing tests and moving stale files...$(NC)"
	@./scripts/testing/sync_tests_with_source.sh -m
	@echo -e "$(GREEN)✅ Test sync complete (stale files moved)$(NC)"

# TypeScript Test Synchronization (mirrors apps/*/static/*/ts/ -> tests/ts/)
sync-ts-tests:
	@echo -e "$(CYAN)🔄 Synchronizing TypeScript test files with source...$(NC)"
	@./scripts/testing/sync_ts_tests_with_source.sh $(if $(MOVE),-m,)
	@echo -e "$(GREEN)✅ TypeScript test sync complete$(NC)"

sync-ts-tests-move:
	@echo -e "$(CYAN)🔄 Synchronizing TS tests and moving stale files...$(NC)"
	@./scripts/testing/sync_ts_tests_with_source.sh -m
	@echo -e "$(GREEN)✅ TypeScript test sync complete (stale files moved)$(NC)"

# TypeScript Testing with Vitest
setup-vitest:
	@echo -e "$(CYAN)🔧 Setting up Vitest testing infrastructure...$(NC)"
	@./scripts/testing/setup_vitest.sh
	@echo -e "$(GREEN)✅ Vitest setup complete$(NC)"

test-ts:
	@if ! npm list vitest --depth=0 >/dev/null 2>&1; then \
		echo -e "$(RED)❌ Vitest not installed. Run: make setup-vitest$(NC)"; \
		exit 1; \
	fi
	@echo -e "$(CYAN)🧪 Running TypeScript tests...$(NC)"
	@npm run test:run

test-ts-watch:
	@if ! npm list vitest --depth=0 >/dev/null 2>&1; then \
		echo -e "$(RED)❌ Vitest not installed. Run: make setup-vitest$(NC)"; \
		exit 1; \
	fi
	@echo -e "$(CYAN)🧪 Running TypeScript tests (watch mode)...$(NC)"
	@npm run test

test-ts-ui:
	@if ! npm list vitest --depth=0 >/dev/null 2>&1; then \
		echo -e "$(RED)❌ Vitest not installed. Run: make setup-vitest$(NC)"; \
		exit 1; \
	fi
	@echo -e "$(CYAN)🧪 Opening Vitest UI...$(NC)"
	@npm run test:ui

test-ts-coverage:
	@if ! npm list vitest --depth=0 >/dev/null 2>&1; then \
		echo -e "$(RED)❌ Vitest not installed. Run: make setup-vitest$(NC)"; \
		exit 1; \
	fi
	@echo -e "$(CYAN)🧪 Running TypeScript tests with coverage...$(NC)"
	@npm run test:coverage

# Python Testing with Pytest
setup-pytest:
	@./scripts/testing/setup_pytest.sh

setup-testing: setup-pytest setup-vitest
	@echo -e "$(GREEN)✅ All testing infrastructure setup complete$(NC)"

test-unit:
	@./scripts/testing/run_tests.sh unit

test-db:
	@./scripts/testing/run_tests.sh db

test-api:
	@./scripts/testing/run_tests.sh api

test-ui:
	@./scripts/testing/run_tests.sh ui

test-ui-headed:
	@./scripts/testing/run_tests.sh ui --headed

test-python:
	@./scripts/testing/run_tests.sh python

test-all:
	@./scripts/testing/run_tests.sh all

test-status:
	@./scripts/testing/run_tests.sh --check

# ============================================
# Database Commands
# ============================================
db-shell: validate
	@echo -e "$(CYAN)🗄️  Opening database shell ($(ENV))...$(NC)"
	@cd $(DOCKER_DIR) && $(MAKE) -f Makefile db-shell

db-backup: validate
	@echo -e "$(CYAN)💾 Backing up database ($(ENV))...$(NC)"
	@cd $(DOCKER_DIR) && $(MAKE) -f Makefile db-backup

db-reset: validate
	@if [ "$(ENV)" != "dev" ]; then \
		echo -e "$(RED)❌ db-reset only available in dev environment$(NC)"; \
		exit 1; \
	fi
	@echo -e "$(YELLOW)⚠️  Resetting database (dev only)...$(NC)"
	@cd $(DOCKER_DIR) && $(MAKE) -f Makefile db-reset

# ============================================
# Fresh Start (Complete Reset)
# ============================================
fresh-start: validate
	@if [ "$(ENV)" != "dev" ]; then \
		echo -e "$(RED)❌ fresh-start only available in dev environment$(NC)"; \
		echo -e "$(YELLOW)   This is a destructive operation meant for development$(NC)"; \
		exit 1; \
	fi
	@echo -e ""
	@echo -e "$(RED)╔═══════════════════════════════════════════════════════╗$(NC)"
	@echo -e "$(RED)║           ⚠️  COMPLETE FRESH START ⚠️                 ║$(NC)"
	@echo -e "$(RED)╚═══════════════════════════════════════════════════════╝$(NC)"
	@echo -e ""
	@echo -e "$(CYAN)📊 Current System State:$(NC)"
	@echo -e ""
	@# Show database info
	@USERS=$$(docker exec scitex-cloud-dev-django-1 python manage.py shell -c "from django.contrib.auth.models import User; print(User.objects.count())" 2>/dev/null | tail -1); \
	PROJECTS=$$(docker exec scitex-cloud-dev-django-1 python manage.py shell -c "from apps.project_app.models import Project; print(Project.objects.count())" 2>/dev/null | tail -1); \
	MANUSCRIPTS=$$(docker exec scitex-cloud-dev-django-1 python manage.py shell -c "from apps.writer_app.models import Manuscript; print(Manuscript.objects.count())" 2>/dev/null | tail -1); \
	REPOS=$$(docker exec scitex-cloud-dev-db-1 psql -U scitex_dev -d scitex_cloud_dev -t -c "SELECT COUNT(*) FROM repository;" 2>/dev/null | xargs); \
	DB_SIZE=$$(docker exec scitex-cloud-dev-db-1 du -sh /var/lib/postgresql/data 2>/dev/null | cut -f1); \
	GITEA_SIZE=$$(docker exec scitex-cloud-dev-gitea-1 du -sh /data 2>/dev/null | cut -f1); \
	USER_SIZE=$$(du -sh ./data/users/ 2>/dev/null | cut -f1); \
	echo -e "  $(YELLOW)Database:$(NC)"; \
	echo "    • Users: $$USERS"; \
	echo "    • Projects: $$PROJECTS"; \
	echo "    • Manuscripts: $$MANUSCRIPTS"; \
	echo "    • Size: $$DB_SIZE"; \
	echo ""; \
	echo -e "  $(YELLOW)Gitea:$(NC)"; \
	echo "    • Repositories: $$REPOS"; \
	echo "    • Size: $$GITEA_SIZE"; \
	echo ""; \
	echo -e "  $(YELLOW)User Files:$(NC)"; \
	echo "    • Total Size: $$USER_SIZE"; \
	echo -e "    • Directories: $$(ls -1 ./data/users/ 2>/dev/null | wc -l)"; \
	echo ""
	@echo -e "$(RED)⚠️  THIS WILL DELETE:$(NC)"
	@echo -e "  • All database tables (Django + Gitea)"
	@echo -e "  • All user directories (./data/users/*)"
	@echo -e "  • All Gitea repositories"
	@echo -e "  • All Docker volumes"
	@echo -e ""
	@echo -e "$(GREEN)✓ What's PRESERVED:$(NC)"
	@echo -e "  • Source code (apps/, config/, scripts/)"
	@echo -e "  • Docker images (no rebuild needed)"
	@echo -e "  • Configuration files (.env, settings)"
	@echo -e "  • Static files (CSS, JS, templates)"
	@echo -e "  • Python packages (.venv in project root)"
	@echo -e ""
	@echo -e "$(GREEN)Then it will:$(NC)"
	@echo -e "  • Recreate database with migrations"
	@echo -e "  • Initialize visitor pool (4 accounts)"
	@echo -e "  • Create fresh Gitea instance"
	@echo -e ""
	@echo -e "$(YELLOW)⚠️  Note: Will ask for sudo password to delete Docker-created files$(NC)"
	@echo -e ""
	@printf "$(YELLOW)Type 'DELETE EVERYTHING' to confirm: $(NC)"; \
	read confirm; \
	if [ "$$confirm" != "DELETE EVERYTHING" ]; then \
		echo -e "$(GREEN)✅ Cancelled - no changes made$(NC)"; \
		exit 0; \
	fi
	@echo -e ""
	@echo -e "$(CYAN)🔄 Starting complete fresh start...$(NC)"
	@echo -e ""
	@# Step 1: Stop all containers
	@echo -e "$(CYAN)Step 1/6: Stopping all containers...$(NC)"
	@$(MAKE) --no-print-directory stop-all
	@echo -e ""
	@# Step 2: Remove volumes
	@echo -e "$(CYAN)Step 2/6: Removing Docker volumes...$(NC)"
	@docker volume rm -f scitex-cloud-dev_postgres_data scitex-cloud-dev_gitea_data 2>/dev/null || true
	@echo -e "$(GREEN)✓ Volumes removed$(NC)"
	@echo -e ""
	@# Step 3: Clean data directories
	@echo -e "$(CYAN)Step 3/6: Cleaning data directories...$(NC)"
	@echo -e "  Removing ./data/users/* (requires sudo for Docker-created files)..."
	@if [ -d ./data/users ] && [ "$$(ls -A ./data/users 2>/dev/null)" ]; then \
		sudo rm -rf ./data/users/* || { \
			echo -e "$(RED)❌ Failed to remove user directories. Try: sudo rm -rf ./data/users/*$(NC)"; \
			exit 1; \
		}; \
	fi
	@echo -e "  Removing ./logs/*..."
	@rm -rf ./logs/*.log 2>/dev/null || true
	@echo -e "$(GREEN)✓ Directories cleaned$(NC)"
	@echo -e ""
	@# Step 4: Start containers
	@echo -e "$(CYAN)Step 4/6: Starting fresh containers...$(NC)"
	@$(MAKE) --no-print-directory ENV=dev start
	@echo -e ""
	@# Step 5: Wait for services
	@echo -e "$(CYAN)Step 5/6: Waiting for services to be ready...$(NC)"
	@echo -e "  Waiting 15 seconds for database and Gitea..."
	@sleep 15
	@echo -e "$(GREEN)✓ Services ready$(NC)"
	@echo -e ""
	@# Step 6: Initialize visitor pool
	@echo -e "$(CYAN)Step 6/6: Initializing visitor pool...$(NC)"
	@docker exec scitex-cloud-dev-django-1 python manage.py create_visitor_pool
	@echo -e ""
	@echo -e "$(GREEN)╔═══════════════════════════════════════════════════════╗$(NC)"
	@echo -e "$(GREEN)║            ✨ FRESH START COMPLETE! ✨                ║$(NC)"
	@echo -e "$(GREEN)╚═══════════════════════════════════════════════════════╝$(NC)"
	@echo -e ""
	@echo -e "$(CYAN)🎉 Your development environment is now clean:$(NC)"
	@echo -e "  • Database: Fresh with migrations applied"
	@echo -e "  • Visitor pool: 4 accounts ready (rotated automatically)"
	@echo -e "  • Gitea: Fresh instance"
	@echo -e "  • Files: Clean slate"
	@echo -e ""
	@echo -e "$(CYAN)📝 Next steps:$(NC)"
	@echo -e "  1. Create superuser: make ENV=dev createsuperuser"
	@echo -e "  2. Access dev server: http://localhost:8000"
	@echo -e "  3. Access Gitea: http://localhost:3001"
	@echo -e ""

# Quick fresh start without confirmation (for scripts/automation)
fresh-start-confirm: validate
	@if [ "$(ENV)" != "dev" ]; then \
		echo -e "$(RED)❌ fresh-start-confirm only available in dev environment$(NC)"; \
		exit 1; \
	fi
	@echo -e "$(YELLOW)⚠️  Running fresh start without confirmation...$(NC)"
	@$(MAKE) --no-print-directory stop-all
	@docker volume rm -f scitex-cloud-dev_postgres_data scitex-cloud-dev_gitea_data 2>/dev/null || true
	@rm -rf ./data/users/*
	@rm -rf ./logs/*.log
	@$(MAKE) --no-print-directory ENV=dev start
	@sleep 15
	@docker exec scitex-cloud-dev-django-1 python manage.py create_visitor_pool
	@echo -e "$(GREEN)✅ Fresh start complete$(NC)"

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
	@echo -e "$(CYAN)🐳 Opening shell in web container ($(ENV))...$(NC)"
	@cd $(DOCKER_DIR) && $(MAKE) -f Makefile exec-web

exec-db: validate
	@echo -e "$(CYAN)🐳 Opening shell in database container ($(ENV))...$(NC)"
	@cd $(DOCKER_DIR) && $(MAKE) -f Makefile exec-db

# Execute arbitrary command in web container
# Usage: make ENV=dev exec CMD="ls -la" or make ENV=dev exec ls -la
exec: validate
	@if [ -z "$(CMD)" ]; then \
		echo -e "$(YELLOW)⚠️  No CMD specified, using remaining args: $(filter-out $@,$(MAKECMDGOALS))$(NC)"; \
		cd $(DOCKER_DIR) && docker compose exec web $(filter-out $@,$(MAKECMDGOALS)); \
	else \
		echo -e "$(CYAN)🐳 Executing command in web container ($(ENV)): $(CMD)$(NC)"; \
		cd $(DOCKER_DIR) && docker compose exec web $(CMD); \
	fi

# Catch-all rule to prevent "No rule to make target" errors when using exec
%:
	@:

exec-gitea: validate
	@echo -e "$(CYAN)🐳 Opening shell in Gitea container ($(ENV))...$(NC)"
	@cd $(DOCKER_DIR) && $(MAKE) -f Makefile exec-gitea 2>/dev/null || echo "$(YELLOW)Gitea not available in $(ENV)$(NC)"

list-envs: validate
	@echo -e "$(CYAN)🔍 Environment variables in $(ENV):$(NC)"
	@docker exec scitex-cloud-$(ENV)-web-1 env | sort

# ============================================
# Dev-Only Commands
# ============================================
gitea-token:
ifeq ($(ENV),dev)
	@echo -e "$(CYAN)🔑 Setting up Gitea token (dev)...$(NC)"
	cd $(DOCKER_DIR) && $(MAKE) -f Makefile gitea-token
else
	@echo -e "$(YELLOW)❌ gitea-token only available in dev environment$(NC)"
	@exit 1
endif

recreate-testuser:
ifeq ($(ENV),dev)
	@echo -e "$(CYAN)👤 Recreating test user (dev)...$(NC)"
	cd $(DOCKER_DIR) && $(MAKE) -f Makefile recreate-testuser
else
	@echo -e "$(YELLOW)❌ recreate-testuser only available in dev environment$(NC)"
	@exit 1
endif

# ============================================
# Health Checks
# ============================================
verify-health: validate
	@if [ "$(ENV)" = "dev" ]; then \
		echo -e "$(YELLOW)❌ verify-health only available in nas$(NC)"; \
		exit 1; \
	fi
	@cd $(DOCKER_DIR) && $(MAKE) -f Makefile verify-health

# ============================================
# Utilities
# ============================================
clean-python:
	@cd $(DOCKER_DIR) && $(MAKE) -f Makefile clean-python

clean-js:
	@echo -e "$(CYAN)🧹 Cleaning stale JS files from TypeScript directories...$(NC)"
	@./scripts/maintenance/clean_stale_js.sh
	@echo -e "$(GREEN)✅ Done! Run 'make env=dev restart' to apply changes$(NC)"

ensure-executable:
	@./scripts/maintenance/ensure_executable.sh

# ============================================
# Code Quality (Format + Lint)
# ============================================
format: format-python format-web format-shell
	@echo -e ""
	@echo -e "$(GREEN)✅ All formatting and linting complete!$(NC)"

format-python:
	@echo -e "$(CYAN)🐍 Formatting and linting Python code with Ruff...$(NC)"
	@if command -v ruff >/dev/null 2>&1; then \
		ruff format apps/ --respect-gitignore --quiet || echo "$(YELLOW)⚠️  Ruff formatting completed with warnings$(NC)"; \
		ruff check --fix apps/ --exclude migrations --respect-gitignore --quiet || echo "$(RED)❌ Ruff found errors$(NC)"; \
		echo -e "$(GREEN)✅ Python formatting and linting complete!$(NC)"; \
	else \
		echo -e "$(RED)❌ Ruff not found. Install with: pip install ruff$(NC)"; \
		exit 1; \
	fi

format-web:
	@echo -e ""
	@echo -e "$(RED)⚠️  WARNING: This command will MODIFY your files!$(NC)"
	@echo -e "$(YELLOW)   • djLint will reformat Django templates$(NC)"
	@echo -e "$(YELLOW)   • Prettier will reformat JS/TS/CSS$(NC)"
	@echo -e "$(YELLOW)   • ESLint --fix will auto-fix code violations$(NC)"
	@echo -e ""
	@echo -e "$(CYAN)💡 For read-only checking (SAFE): make lint-web$(NC)"
	@echo -e ""
	@printf "$(YELLOW)Type 'yes' to continue with formatting: $(NC)"; \
	read confirm; \
	if [ "$$confirm" != "yes" ]; then \
		echo -e "$(GREEN)✅ Cancelled - no changes made$(NC)"; \
		exit 0; \
	fi
	@echo -e ""
	@echo -e "$(CYAN)✨ Formatting and linting web files...$(NC)"
	@echo -e "$(CYAN)📝 Formatting Django templates with djLint...$(NC)"
	@if command -v djlint >/dev/null 2>&1; then \
		djlint --reformat --quiet \
			apps/ templates/ \
			2>&1 || echo "$(YELLOW)⚠️  djLint formatting completed with warnings$(NC)"; \
		echo -e "$(GREEN)✅ Django template formatting complete!$(NC)"; \
	else \
		echo -e "$(YELLOW)⚠️  djLint not found. Install with: pip install djlint$(NC)"; \
		echo -e "$(YELLOW)   Skipping Django template formatting...$(NC)"; \
	fi
	@echo -e "$(CYAN)💅 Formatting JS/TS/CSS with Prettier...$(NC)"
	@if command -v prettier >/dev/null 2>&1; then \
		prettier --write \
			"apps/**/*.{ts,js,css}" \
			"static/**/*.{ts,js,css}" \
			--ignore-path .gitignore \
			--log-level warn \
			2>&1 || echo "$(YELLOW)⚠️  Prettier formatting completed with warnings$(NC)"; \
		echo -e "$(GREEN)✅ Prettier formatting complete!$(NC)"; \
	else \
		echo -e "$(RED)❌ Prettier not found. Install with: npm install -g prettier$(NC)"; \
		exit 1; \
	fi
	@echo -e "$(CYAN)🔍 Linting TS/JS with ESLint --fix...$(NC)"
	@if command -v eslint >/dev/null 2>&1; then \
		eslint --fix \
			"apps/**/*.{ts,js}" \
			"static/**/*.{ts,js}" \
			--ignore-path .gitignore \
			--quiet \
			2>&1 || echo "$(RED)❌ ESLint found errors$(NC)"; \
		echo -e "$(GREEN)✅ ESLint linting complete!$(NC)"; \
	else \
		echo -e "$(RED)❌ ESLint not found. Install with: npm install -g eslint$(NC)"; \
		exit 1; \
	fi

format-shell:
	@echo -e "$(CYAN)🐚 Formatting and linting shell scripts...$(NC)"
	@if command -v shfmt >/dev/null 2>&1; then \
		find scripts/ deployment/ apps/ -name "*.sh" \
			! -path "*/externals/*" \
			! -path "*/node_modules/*" \
			! -path "*/.venv/*" \
			-exec shfmt -w -i 4 -bn -ci -sr {} + \
			2>&1 || echo "$(YELLOW)⚠️  shfmt formatting completed with warnings$(NC)"; \
		echo -e "$(GREEN)✅ Shell formatting complete!$(NC)"; \
	else \
		echo -e "$(YELLOW)⚠️  shfmt not found. Install with: go install mvdan.cc/sh/v3/cmd/shfmt@latest$(NC)"; \
		echo -e "$(YELLOW)   Skipping shell formatting...$(NC)"; \
	fi
	@if command -v shellcheck >/dev/null 2>&1; then \
		find scripts/ deployment/ apps/ -name "*.sh" \
			! -path "*/externals/*" \
			! -path "*/node_modules/*" \
			! -path "*/.venv/*" \
			-exec shellcheck --severity=error {} + \
			2>&1 || echo "$(RED)❌ ShellCheck found errors$(NC)"; \
		echo -e "$(GREEN)✅ Shell linting complete!$(NC)"; \
	else \
		echo -e "$(YELLOW)⚠️  shellcheck not found. Install with: sudo apt-get install shellcheck$(NC)"; \
		echo -e "$(YELLOW)   Skipping shell linting...$(NC)"; \
	fi

# ============================================
# Linting (Read-Only - SAFE)
# ============================================
lint: lint-web
	@echo -e ""
	@echo -e "$(GREEN)✅ All linting checks complete (no files modified)!$(NC)"

lint-web:
	@echo -e "$(GREEN)✅ SAFE MODE: Checking files without making changes$(NC)"
	@echo -e ""
	@echo -e "$(CYAN)🔍 Checking TS/JS with ESLint (read-only)...$(NC)"
	@if command -v eslint >/dev/null 2>&1; then \
		npx eslint \
			"apps/**/*.{ts,js}" \
			"static/**/*.{ts,js}" \
			2>&1 | head -100 || true; \
		echo ""; \
		echo -e "$(GREEN)✅ ESLint check complete!$(NC)"; \
		echo -e "$(CYAN)💡 To auto-fix issues: make format-web$(NC)"; \
	else \
		echo -e "$(RED)❌ ESLint not found. Install with: npm install -g eslint$(NC)"; \
		exit 1; \
	fi
	@echo -e ""
	@echo -e "$(CYAN)💅 Checking JS/TS/CSS with Prettier (read-only)...$(NC)"
	@if command -v prettier >/dev/null 2>&1; then \
		prettier --check \
			"apps/**/*.{ts,js,css}" \
			"static/**/*.{ts,js,css}" \
			--ignore-path .gitignore \
			--log-level warn \
			2>&1 | head -50 || true; \
		echo ""; \
		echo -e "$(GREEN)✅ Prettier check complete!$(NC)"; \
	else \
		echo -e "$(RED)❌ Prettier not found. Install with: npm install -g prettier$(NC)"; \
		exit 1; \
	fi

# ============================================
# File Size Checks
# ============================================
check-file-sizes:
	@echo -e "$(CYAN)📏 Checking file sizes (>300 line threshold)...$(NC)"
	@./scripts/maintenance/check_file_sizes.sh --verbose

# ============================================
# Asset Tracking Checks
# ============================================
check-assets:
	@./scripts/maintenance/check_untracked_assets.sh

# ============================================
# Host Requirements Checks
# ============================================
check-host:
	@echo -e "$(CYAN)🔍 Checking host requirements...$(NC)"
	@echo -e ""
	@# Pass ENV if set, otherwise script auto-detects from running containers
	@deployment/host-setup/checks/check-users.sh $(ENV) || true
	@echo -e ""
	@deployment/host-setup/checks/check-slurm.sh || true
	@echo -e ""
	@echo -e "$(CYAN)🖥️  Terminal Functionality:$(NC)"
	@deployment/host-setup/checks/check-terminal-ready.sh $(ENV) || true
	@echo -e ""

# ============================================
# Info
# ============================================
info:
	@echo -e "Specified environment: $(ENV)"
	@echo -e "Running environments: $$(docker ps --format '{{.Names}}' 2>/dev/null | grep -oE 'scitex-cloud-(dev|prod|nas)-' | sed 's/scitex-cloud-//' | sed 's/-//' | sort -u | tr '\n' ' ')"
	@echo -e "Container directory: $(DOCKER_DIR)"
	@echo -e "Makefile: $(MAKEFILE)"

# ============================================
# CrossRef Database Management
# ============================================
.PHONY: crossref-status crossref-check crossref-rebuild-check crossref-create-title-index crossref-create-author-index crossref-next-steps

crossref-status:
	@echo -e "$(CYAN)📊 CrossRef Citations Rebuild Status$(NC)"
	@echo -e ""
	@echo -e "$(YELLOW)⚠️  IMPORTANT REMINDER:$(NC)"
	@echo -e "  Started: Dec 4, 2025 ~22:50"
	@echo -e "  Expected completion: ~Dec 9-10, 2025 (5 days)"
	@echo -e ""
	@echo -e "$(CYAN)Screen session:$(NC)"
	@screen -ls | grep citations-rebuild || echo -e "  $(RED)❌ Screen session not found$(NC)"
	@echo -e ""
	@echo -e "$(CYAN)Process status:$(NC)"
	@ps aux | grep rebuild_citations_table.py | grep -v grep | head -3 || echo -e "  $(RED)❌ Process not running$(NC)"
	@echo -e ""
	@echo -e "$(CYAN)Latest progress:$(NC)"
	@tail -30 /home/ywatanabe/proj/crossref_local/impact_factor/rebuild_citations_*.log 2>/dev/null | grep -E "Progress|ETA" | tail -5 || echo -e "  $(YELLOW)No log found$(NC)"
	@echo -e ""
	@echo -e "$(CYAN)Database info:$(NC)"
	@du -h /home/ywatanabe/proj/crossref_local/data/crossref.db 2>/dev/null | awk '{print "  Size: " $$1}' || echo -e "  $(YELLOW)Database not found$(NC)"
	@sqlite3 /home/ywatanabe/proj/crossref_local/data/crossref.db "SELECT COUNT(*) FROM citations;" 2>/dev/null | awk '{print "  Citations: " $$0}' || echo -e "  $(YELLOW)Table not accessible$(NC)"
	@echo -e ""
	@echo -e "$(CYAN)To attach to screen session:$(NC)"
	@echo -e "  screen -r citations-rebuild"

crossref-check: crossref-rebuild-check

crossref-rebuild-check:
	@echo -e "$(CYAN)🔍 Checking if Citations Rebuild is Complete$(NC)"
	@echo -e ""
	@if ps aux | grep rebuild_citations_table.py | grep -v grep > /dev/null; then \
		echo -e "$(YELLOW)⏳ Citations rebuild is STILL RUNNING$(NC)"; \
		echo ""; \
		echo -e "$(CYAN)Current progress:$(NC)"; \
		tail -30 /home/ywatanabe/proj/crossref_local/impact_factor/rebuild_citations_*.log 2>/dev/null | grep Progress | tail -1; \
		echo ""; \
		echo -e "$(CYAN)💡 Commands:$(NC)"; \
		echo "  make crossref-status         # Detailed status"; \
		echo "  screen -r citations-rebuild  # Attach to screen"; \
		echo ""; \
		echo -e "$(RED)❌ NOT READY for next steps yet$(NC)"; \
	else \
		echo -e "$(GREEN)✅ Citations rebuild appears to be COMPLETE!$(NC)"; \
		echo ""; \
		echo -e "$(CYAN)Verification:$(NC)"; \
		sqlite3 /home/ywatanabe/proj/crossref_local/data/crossref.db "SELECT COUNT(*) FROM citations;" 2>/dev/null | awk '{print "  Total citations: " $$0}' || echo -e "  $(YELLOW)Cannot verify$(NC)"; \
		echo ""; \
		echo -e "$(GREEN)✅ Ready for next steps!$(NC)"; \
		echo ""; \
		echo "  make crossref-next-steps     # Show optimization steps"; \
	fi

crossref-next-steps:
	@echo -e "$(CYAN)╔═══════════════════════════════════════════════════════╗$(NC)"
	@echo -e "$(CYAN)║    📋 Next Steps: CrossRef API Optimization           ║$(NC)"
	@echo -e "$(CYAN)╚═══════════════════════════════════════════════════════╝$(NC)"
	@echo -e ""
	@echo -e "$(GREEN)✅ Citations rebuild is complete!$(NC)"
	@echo -e ""
	@echo -e "$(CYAN)📊 Current API Status:$(NC)"
	@echo -e "  Port 8000 (Django):  ✅ All searches work (DOI, title, year, authors)"
	@echo -e "  Port 3333 (FastAPI): ⚠️  Only DOI works, title/author/year broken"
	@echo -e ""
	@echo -e "$(CYAN)🔧 Required Optimizations:$(NC)"
	@echo -e ""
	@echo -e "$(YELLOW)1. Create Title Index$(NC) (~4-8 hours)"
	@echo -e "   Enables fast title searches on port 3333"
	@echo -e "   Command: $(GREEN)make crossref-create-title-index$(NC)"
	@echo -e ""
	@echo -e "$(YELLOW)2. Create Author Index$(NC) (~4-8 hours)"
	@echo -e "   Enables fast author searches on port 3333"
	@echo -e "   Command: $(GREEN)make crossref-create-author-index$(NC)"
	@echo -e ""
	@echo -e "$(YELLOW)3. Update FastAPI Code$(NC)"
	@echo -e "   File: deployment/crossref/database.py"
	@echo -e "   Update search_by_metadata() to use JSON queries"
	@echo -e "   See: /home/ywatanabe/proj/crossref_local/impact_factor/docs/API_OPTIMIZATION.md"
	@echo -e ""
	@echo -e "$(CYAN)💡 Recommended order:$(NC)"
	@echo -e "  1. Run both index creation commands (can do overnight)"
	@echo -e "  2. Update FastAPI code"
	@echo -e "  3. Restart port 3333 service"
	@echo -e "  4. Test all search types work on both ports"
	@echo -e ""
	@echo -e "$(CYAN)📚 Documentation:$(NC)"
	@echo -e "  /home/ywatanabe/proj/crossref_local/impact_factor/NEXT_STEPS_AFTER_REBUILD.md"
	@echo -e ""

crossref-create-title-index:
	@echo -e "$(CYAN)═══════════════════════════════════════════════════════$(NC)"
	@echo -e "$(CYAN)    📊 Creating Title Index on CrossRef Database        $(NC)"
	@echo -e "$(CYAN)═══════════════════════════════════════════════════════$(NC)"
	@echo -e ""
	@echo -e "$(YELLOW)⚠️  WARNING:$(NC)"
	@echo -e "  • This will take ~4-8 hours"
	@echo -e "  • Database will be under heavy load"
	@echo -e "  • Do NOT interrupt or run other DB operations"
	@echo -e "  • Port 3333 API may be slow during this time"
	@echo -e ""
	@echo -e "$(CYAN)Index details:$(NC)"
	@echo -e "  Database: /home/ywatanabe/proj/crossref_local/data/crossref.db"
	@echo -e "  Table: works (167M rows)"
	@echo -e "  Field: json_extract(metadata, '\$$.title[0]')"
	@echo -e ""
	@printf "$(YELLOW)Type 'yes' to continue: $(NC)"; \
	read confirm; \
	if [ "$$confirm" = "yes" ]; then \
		echo ""; \
		echo -e "$(CYAN)Starting index creation...$(NC)"; \
		echo "  Started at: $$(date '+%Y-%m-%d %H:%M:%S')"; \
		echo ""; \
		START_TIME=$$(date +%s); \
		sqlite3 /home/ywatanabe/proj/crossref_local/data/crossref.db "CREATE INDEX IF NOT EXISTS idx_title ON works(json_extract(metadata, '\$$.title[0]'));" && \
		END_TIME=$$(date +%s); \
		DURATION=$$((END_TIME - START_TIME)); \
		echo ""; \
		echo -e "$(GREEN)✅ Title index created successfully!$(NC)"; \
		echo "  Completed at: $$(date '+%Y-%m-%d %H:%M:%S')"; \
		echo "  Duration: $$((DURATION / 3600))h $$((DURATION % 3600 / 60))m $$((DURATION % 60))s"; \
		echo ""; \
		echo -e "$(CYAN)Next step:$(NC)"; \
		echo "  make crossref-create-author-index  # Create author index"; \
	else \
		echo -e "$(GREEN)✅ Cancelled$(NC)"; \
	fi

crossref-create-author-index:
	@echo -e "$(CYAN)═══════════════════════════════════════════════════════$(NC)"
	@echo -e "$(CYAN)    👥 Creating Author Index on CrossRef Database       $(NC)"
	@echo -e "$(CYAN)═══════════════════════════════════════════════════════$(NC)"
	@echo -e ""
	@echo -e "$(YELLOW)⚠️  WARNING:$(NC)"
	@echo -e "  • This will take ~4-8 hours"
	@echo -e "  • Database will be under heavy load"
	@echo -e "  • Do NOT interrupt or run other DB operations"
	@echo -e "  • Port 3333 API may be slow during this time"
	@echo -e ""
	@echo -e "$(CYAN)Index details:$(NC)"
	@echo -e "  Database: /home/ywatanabe/proj/crossref_local/data/crossref.db"
	@echo -e "  Table: works (167M rows)"
	@echo -e "  Field: json_extract(metadata, '\$$.author')"
	@echo -e ""
	@printf "$(YELLOW)Type 'yes' to continue: $(NC)"; \
	read confirm; \
	if [ "$$confirm" = "yes" ]; then \
		echo ""; \
		echo -e "$(CYAN)Starting index creation...$(NC)"; \
		echo "  Started at: $$(date '+%Y-%m-%d %H:%M:%S')"; \
		echo ""; \
		START_TIME=$$(date +%s); \
		sqlite3 /home/ywatanabe/proj/crossref_local/data/crossref.db "CREATE INDEX IF NOT EXISTS idx_author ON works(json_extract(metadata, '\$$.author'));" && \
		END_TIME=$$(date +%s); \
		DURATION=$$((END_TIME - START_TIME)); \
		echo ""; \
		echo -e "$(GREEN)✅ Author index created successfully!$(NC)"; \
		echo "  Completed at: $$(date '+%Y-%m-%d %H:%M:%S')"; \
		echo "  Duration: $$((DURATION / 3600))h $$((DURATION % 3600 / 60))m $$((DURATION % 60))s"; \
		echo ""; \
		echo -e "$(CYAN)Next steps:$(NC)"; \
		echo "  1. Update FastAPI code to use JSON queries"; \
		echo "  2. make crossref-next-steps  # See full instructions"; \
	else \
		echo -e "$(GREEN)✅ Cancelled$(NC)"; \
	fi

# ============================================
# SLURM Management
# ============================================
slurm-start:
	@echo -e "$(CYAN)🚀 Starting SLURM services...$(NC)"
	@echo -e "  Starting munge..."
	@sudo systemctl start munge 2>&1 || sudo service munge start 2>&1 || echo "$(YELLOW)  munge may already be running$(NC)"
	@echo -e "  Starting slurmctld..."
	@sudo systemctl start slurmctld 2>&1 || sudo service slurmctld start 2>&1 || echo "$(RED)  Failed to start slurmctld$(NC)"
	@echo -e "  Starting slurmd..."
	@sudo systemctl start slurmd 2>&1 || sudo service slurmd start 2>&1 || echo "$(RED)  Failed to start slurmd$(NC)"
	@sleep 2
	@$(MAKE) slurm-status

slurm-stop:
	@echo -e "$(YELLOW)⏹️  Stopping SLURM services...$(NC)"
	@sudo systemctl stop slurmd slurmctld 2>/dev/null || \
		(sudo service slurmd stop && sudo service slurmctld stop) 2>/dev/null || \
		echo -e "$(RED)❌ Failed to stop SLURM$(NC)"
	@$(MAKE) slurm-status

slurm-restart:
	@echo -e "$(CYAN)🔄 Restarting SLURM services...$(NC)"
	@$(MAKE) slurm-stop
	@sleep 1
	@$(MAKE) slurm-start

slurm-status:
	@echo -e "$(CYAN)🖥️  SLURM Status:$(NC)"
	@if command -v sinfo >/dev/null 2>&1; then \
		SLURM_STATUS=$$(sinfo --noheader 2>&1); \
		if [ -n "$$SLURM_STATUS" ] && ! echo "$$SLURM_STATUS" | grep -q "error"; then \
			echo -e "  $(GREEN)✅ SLURM Cluster: OPERATIONAL$(NC)"; \
			echo ""; \
			echo "  Partitions:"; \
			sinfo 2>/dev/null | head -10 | while read line; do echo "    $$line"; done; \
			echo ""; \
			echo "  Jobs:"; \
			squeue 2>/dev/null | head -10 | while read line; do echo "    $$line"; done; \
		else \
			echo -e "  $(RED)❌ SLURM Cluster: NOT RESPONDING$(NC)"; \
			echo -e "  $(YELLOW)💡 To fix: make slurm-fix$(NC)"; \
		fi; \
	else \
		echo -e "  $(YELLOW)⚠️  SLURM not installed$(NC)"; \
	fi

slurm-fix:
	@echo -e "$(CYAN)🔧 Fixing SLURM (requires sudo)...$(NC)"
	@sudo ./deployment/slurm/scripts/07_fix_munge_auth.sh
	@$(MAKE) slurm-status

slurm-resume:
	@echo -e "$(CYAN)🔄 Resuming SLURM nodes...$(NC)"
	@HOSTNAME=$$(hostname); \
	echo "  Resuming node: $$HOSTNAME"; \
	sudo scontrol update nodename=$$HOSTNAME state=resume; \
	sleep 2
	@$(MAKE) slurm-status

slurm-reset:
	@echo -e "$(RED)⚠️  This will clear ALL SLURM jobs and reset state!$(NC)"
	@read -p "Are you sure? (y/N) " confirm && [ "$$confirm" = "y" ] || exit 1
	@sudo ./deployment/slurm/scripts/08_reset_slurm_state.sh
	@$(MAKE) slurm-status

# ============================================
# Gallery Management
# ============================================
regenerate-gallery:
	@echo -e "$(CYAN)🎨 Regenerating plot gallery...$(NC)"
	@./scripts/maintenance/regenerate_gallery.sh
	@echo -e "$(GREEN)✅ Gallery regeneration complete$(NC)"

# EOF
