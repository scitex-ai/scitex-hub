# ============================================
# SciTeX Template Research - Makefile
# ============================================
# Scientific research project workflow automation
# Location: /Makefile
#
# Key Features:
# - Script execution and pipeline management
# - Dependency installation and environment setup
# - Output cleaning and data management
# - Code formatting and quality checks
# - Testing automation
#
# Usage:
#   make help                      # Show this help
#   make install                   # Install dependencies
#   make run-mnist                 # Run MNIST example pipeline
#   make clean                     # Clean outputs
#   make format                    # Format code
#   make test                      # Run tests

.PHONY: \
	help \
	install \
	install-dev \
	setup \
	setup-writer \
	run-mnist \
	run-mnist-download \
	run-mnist-plot-digits \
	run-mnist-plot-umap \
	run-mnist-clf-svm \
	run-mnist-conf-mat \
	clean \
	clean-mnist \
	clean-outputs \
	clean-data \
	clean-logs \
	clean-all \
	clean-python \
	clean-writer \
	test \
	test-verbose \
	test-sync \
	format \
	format-python \
	format-shell \
	lint \
	lint-python \
	check \
	info \
	tree \
	verify \
	show-config

.DEFAULT_GOAL := help

# ============================================
# Configuration
# ============================================
PYTHON := python3
PIP := pip3
SCRIPTS_DIR := scripts
MNIST_DIR := $(SCRIPTS_DIR)/mnist
CONFIG_DIR := config
DATA_DIR := data
TESTS_DIR := tests
SCITEX_DIR := scitex
WRITER_DIR := $(SCITEX_DIR)/writer

# Colors
GREEN := \033[0;32m
YELLOW := \033[0;33m
RED := \033[0;31m
CYAN := \033[0;36m
BLUE := \033[0;34m
NC := \033[0m

# ============================================
# Help
# ============================================
help:
	@echo ""
	@echo "$(GREEN)############################################################$(NC)"
	@echo "$(GREEN)#      SciTeX Template Research - Makefile                  $(NC)"
	@echo "$(GREEN)############################################################$(NC)"
	@echo ""
	@echo "$(CYAN)Setup & Installation:$(NC)"
	@echo "  make install                       # Install Python dependencies"
	@echo "  make install-dev                   # Install dev dependencies (testing, linting)"
	@echo "  make setup                         # Complete setup (install + verify)"
	@echo "  make setup-writer                  # Clone writer template project (example_paper)"
	@echo ""
	@echo "$(CYAN)Running Scripts:$(NC)"
	@echo "  make run-mnist                     # Run complete MNIST pipeline"
	@echo "  make run-mnist-download            # Download MNIST data"
	@echo "  make run-mnist-plot-digits         # Plot MNIST digits"
	@echo "  make run-mnist-plot-umap           # Create UMAP visualization"
	@echo "  make run-mnist-clf-svm             # Train SVM classifier"
	@echo "  make run-mnist-conf-mat            # Plot confusion matrix"
	@echo ""
	@echo "$(CYAN)Cleaning:$(NC)"
	@echo "  make clean                         # Clean script outputs"
	@echo "  make clean-mnist                   # Clean MNIST outputs only"
	@echo "  make clean-outputs                 # Clean all *_out directories"
	@echo "  make clean-data                    # Clean generated data files"
	@echo "  make clean-logs                    # Clean log files"
	@echo "  make clean-writer                  # Remove writer projects (use with caution!)"
	@echo "  make clean-all                     # Clean everything (outputs + data + cache)"
	@echo "  make clean-python                  # Clean Python cache files"
	@echo ""
	@echo "$(CYAN)Code Quality:$(NC)"
	@echo "  make format                        # Format all code (Python + Shell)"
	@echo "  make format-python                 # Format Python with ruff"
	@echo "  make format-shell                  # Format shell with shfmt + shellcheck"
	@echo "  make lint                          # Lint code with ruff"
	@echo "  make check                         # Run format + lint + test"
	@echo ""
	@echo "$(CYAN)Testing:$(NC)"
	@echo "  make test                          # Run all tests"
	@echo "  make test-verbose                  # Run tests with verbose output"
	@echo "  make test-sync                     # Sync test structure with scripts"
	@echo ""
	@echo "$(CYAN)Information:$(NC)"
	@echo "  make info                          # Show project information"
	@echo "  make tree                          # Show project structure"
	@echo "  make verify                        # Verify installation and config"
	@echo "  make show-config                   # Display configuration files (requires yq)"
	@echo ""

# ============================================
# Installation & Setup
# ============================================
install:
	@echo "$(CYAN)Installing Python dependencies...$(NC)"
	@if [ -f requirements.txt ]; then \
		$(PIP) install -r requirements.txt; \
		echo "$(GREEN)Dependencies installed$(NC)"; \
	else \
		echo "$(RED)requirements.txt not found$(NC)"; \
		exit 1; \
	fi

install-dev:
	@echo "$(CYAN)Installing development dependencies...$(NC)"
	@$(PIP) install pytest pytest-cov ruff black isort mypy
	@echo "$(GREEN)Development dependencies installed$(NC)"

setup: install
	@echo "$(CYAN)Setting up project...$(NC)"
	@mkdir -p $(DATA_DIR)
	@mkdir -p $(DATA_DIR)/mnist/figures
	@mkdir -p $(DATA_DIR)/mnist/models
	@mkdir -p $(DATA_DIR)/mnist/raw
	@echo "$(GREEN)Project setup complete$(NC)"
	@$(MAKE) verify
	@echo ""
	@echo "$(YELLOW)To create a writer project, run:$(NC)"
	@echo "  make setup-writer"
	@echo "  $(YELLOW)or manually:$(NC) scitex writer clone $(WRITER_DIR)/your_paper_name"
	@echo ""

setup-writer:
	@echo "$(CYAN)Setting up writer project...$(NC)"
	@if [ -d "$(WRITER_DIR)/example_paper" ]; then \
		echo "$(YELLOW)Writer project already exists at $(WRITER_DIR)/example_paper$(NC)"; \
		echo "$(YELLOW)To create a new project, use:$(NC)"; \
		echo "  scitex writer clone $(WRITER_DIR)/your_paper_name"; \
		echo ""; \
		echo "$(YELLOW)Git strategies available:$(NC)"; \
		echo "  --git-strategy child   (default: independent git repo)"; \
		echo "  --git-strategy parent  (track in main repo)"; \
		echo "  --git-strategy origin  (preserve template history)"; \
		echo "  --git-strategy none    (no git initialization)"; \
	else \
		echo "$(CYAN)Cloning writer template to $(WRITER_DIR)/example_paper...$(NC)"; \
		scitex writer clone $(WRITER_DIR)/example_paper; \
		echo "$(GREEN)Writer project created successfully!$(NC)"; \
		echo ""; \
		echo "$(CYAN)To compile the manuscript:$(NC)"; \
		echo "  cd $(WRITER_DIR)/example_paper"; \
		echo "  scitex writer compile manuscript"; \
		echo ""; \
		echo "$(YELLOW)Note: Uses 'child' git strategy (independent repository)$(NC)"; \
		echo "$(YELLOW)To use parent repo instead:$(NC)"; \
		echo "  scitex writer clone $(WRITER_DIR)/your_paper --git-strategy parent"; \
		echo ""; \
	fi

verify:
	@echo "$(CYAN)Verifying installation...$(NC)"
	@echo ""
	@echo "$(CYAN)Python version:$(NC)"
	@$(PYTHON) --version
	@echo ""
	@echo "$(CYAN)Checking required packages:$(NC)"
	@for pkg in scitex torch torchvision scikit-learn umap-learn seaborn numpy pandas matplotlib; do \
		if $(PYTHON) -c "import $$pkg" 2>/dev/null; then \
			echo "  $(GREEN)[OK]$(NC) $$pkg"; \
		else \
			echo "  $(RED)[MISSING]$(NC) $$pkg"; \
		fi; \
	done
	@echo ""
	@echo "$(CYAN)Checking configuration files:$(NC)"
	@for cfg in PATH.yaml MNIST.yaml; do \
		if [ -f $(CONFIG_DIR)/$$cfg ]; then \
			echo "  $(GREEN)[OK]$(NC) $$cfg"; \
		else \
			echo "  $(YELLOW)[WARNING]$(NC) $$cfg $(YELLOW)(missing)$(NC)"; \
		fi; \
	done
	@echo ""

# ============================================
# Running MNIST Scripts
# ============================================
run-mnist: run-mnist-download run-mnist-plot-digits run-mnist-plot-umap run-mnist-clf-svm run-mnist-conf-mat
	@echo ""
	@echo "$(GREEN)MNIST pipeline complete!$(NC)"
	@echo ""
	@echo "$(CYAN)Results available in:$(NC)"
	@echo "  - $(DATA_DIR)/mnist/figures/"
	@echo "  - $(MNIST_DIR)/*_out/"

run-mnist-download:
	@echo "$(CYAN)Downloading MNIST dataset...$(NC)"
	@cd $(MNIST_DIR) && $(PYTHON) 01_download.py
	@echo "$(GREEN)Download complete$(NC)"

run-mnist-plot-digits:
	@echo "$(CYAN)Plotting MNIST digits...$(NC)"
	@cd $(MNIST_DIR) && $(PYTHON) 02_plot_digits.py
	@echo "$(GREEN)Plots generated$(NC)"

run-mnist-plot-umap:
	@echo "$(CYAN)Creating UMAP visualization...$(NC)"
	@cd $(MNIST_DIR) && $(PYTHON) 03_plot_umap_space.py
	@echo "$(GREEN)UMAP visualization complete$(NC)"

run-mnist-clf-svm:
	@echo "$(CYAN)Training SVM classifier...$(NC)"
	@cd $(MNIST_DIR) && $(PYTHON) 04_clf_svm.py
	@echo "$(GREEN)SVM training complete$(NC)"

run-mnist-conf-mat:
	@echo "$(CYAN)Plotting confusion matrix...$(NC)"
	@cd $(MNIST_DIR) && $(PYTHON) 05_plot_conf_mat.py
	@echo "$(GREEN)Confusion matrix generated$(NC)"

# ============================================
# Cleaning
# ============================================
clean: clean-outputs clean-logs clean-python
	@echo "$(GREEN)Cleaned outputs and logs$(NC)"

clean-mnist:
	@echo "$(YELLOW)Cleaning MNIST outputs...$(NC)"
	@rm -rf $(MNIST_DIR)/*_out/
	@echo "$(GREEN)MNIST outputs cleaned$(NC)"

clean-outputs:
	@echo "$(YELLOW)Cleaning all script outputs...$(NC)"
	@find $(SCRIPTS_DIR) -type d -name "*_out" -exec rm -rf {} + 2>/dev/null || true
	@echo "$(GREEN)All outputs cleaned$(NC)"

clean-data:
	@echo "$(RED)WARNING: This will delete all generated data files!$(NC)"
	@printf "Type 'yes' to confirm: "; \
	read confirm; \
	if [ "$$confirm" = "yes" ]; then \
		echo "$(YELLOW)Cleaning data directory...$(NC)"; \
		rm -rf $(DATA_DIR)/mnist/*.npy 2>/dev/null || true; \
		rm -rf $(DATA_DIR)/mnist/*.pkl 2>/dev/null || true; \
		rm -rf $(DATA_DIR)/mnist/figures/*.jpg 2>/dev/null || true; \
		rm -rf $(DATA_DIR)/mnist/figures/*.csv 2>/dev/null || true; \
		rm -rf $(DATA_DIR)/mnist/models/*.pkl 2>/dev/null || true; \
		echo "$(GREEN)Data cleaned$(NC)"; \
	else \
		echo "$(YELLOW)Cancelled$(NC)"; \
	fi

clean-logs:
	@echo "$(YELLOW)Cleaning log files...$(NC)"
	@find $(SCRIPTS_DIR) -type f -name "*.log" -delete 2>/dev/null || true
	@find $(SCRIPTS_DIR) -type d -name "RUNNING" -exec rm -rf {}/logs \; 2>/dev/null || true
	@find $(SCRIPTS_DIR) -type d -name "FINISHED_SUCCESS" -exec rm -rf {}/*/logs \; 2>/dev/null || true
	@find $(SCRIPTS_DIR) -type d -name "FINISHED_FAILED" -exec rm -rf {}/*/logs \; 2>/dev/null || true
	@echo "$(GREEN)Logs cleaned$(NC)"

clean-all: clean-outputs clean-data clean-logs clean-python
	@echo "$(RED)WARNING: This will delete ALL generated files!$(NC)"
	@printf "Type 'DELETE ALL' to confirm: "; \
	read confirm; \
	if [ "$$confirm" = "DELETE ALL" ]; then \
		echo "$(YELLOW)Deep cleaning...$(NC)"; \
		rm -rf $(DATA_DIR)/mnist/raw/* 2>/dev/null || true; \
		echo "$(GREEN)Complete cleanup done$(NC)"; \
	else \
		echo "$(YELLOW)Cancelled$(NC)"; \
	fi

clean-python:
	@echo "$(YELLOW)Cleaning Python cache files...$(NC)"
	@find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	@find . -type f -name "*.pyc" -delete 2>/dev/null || true
	@find . -type f -name "*.pyo" -delete 2>/dev/null || true
	@find . -type d -name "*.egg-info" -exec rm -rf {} + 2>/dev/null || true
	@find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	@find . -type d -name ".ruff_cache" -exec rm -rf {} + 2>/dev/null || true
	@find . -type d -name ".mypy_cache" -exec rm -rf {} + 2>/dev/null || true
	@echo "$(GREEN)Python cache cleaned$(NC)"

clean-writer:
	@echo "$(RED)WARNING: This will DELETE all writer projects!$(NC)"
	@echo "$(RED)Each writer project is an independent git repository.$(NC)"
	@echo "$(RED)Make sure you have pushed any uncommitted changes!$(NC)"
	@printf "Type 'DELETE WRITER PROJECTS' to confirm: "; \
	read confirm; \
	if [ "$$confirm" = "DELETE WRITER PROJECTS" ]; then \
		echo "$(YELLOW)Removing all writer projects...$(NC)"; \
		if [ -d "$(WRITER_DIR)" ]; then \
			rm -rf $(WRITER_DIR)/*/; \
			echo "$(GREEN)Writer projects removed$(NC)"; \
		else \
			echo "$(YELLOW)No writer directory found$(NC)"; \
		fi; \
	else \
		echo "$(YELLOW)Cancelled$(NC)"; \
	fi

# ============================================
# Testing
# ============================================
test:
	@echo "$(CYAN)Running tests...$(NC)"
	@if command -v pytest >/dev/null 2>&1; then \
		pytest $(TESTS_DIR) -q; \
	else \
		echo "$(YELLOW)pytest not installed. Run: make install-dev$(NC)"; \
		exit 1; \
	fi

test-verbose:
	@echo "$(CYAN)Running tests (verbose)...$(NC)"
	@if command -v pytest >/dev/null 2>&1; then \
		pytest $(TESTS_DIR) -v; \
	else \
		echo "$(YELLOW)pytest not installed. Run: make install-dev$(NC)"; \
		exit 1; \
	fi

test-sync:
	@echo "$(CYAN)Synchronizing test structure with scripts...$(NC)"
	@$(TESTS_DIR)/sync_tests_with_scripts.sh
	@echo "$(GREEN)Test synchronization complete$(NC)"

# ============================================
# Code Quality
# ============================================
format: format-python format-shell
	@echo ""
	@echo "$(GREEN)All formatting and linting complete!$(NC)"

format-python:
	@echo "$(CYAN)Formatting Python code with ruff...$(NC)"
	@if command -v ruff >/dev/null 2>&1; then \
		ruff format $(SCRIPTS_DIR) $(TESTS_DIR) --quiet || echo "$(YELLOW)Ruff formatting completed with warnings$(NC)"; \
		echo "$(GREEN)Python formatting complete$(NC)"; \
	else \
		echo "$(RED)Ruff not found. Install with: pip install ruff$(NC)"; \
		exit 1; \
	fi

format-shell:
	@echo "$(CYAN)Formatting and linting shell scripts...$(NC)"
	@if command -v shfmt >/dev/null 2>&1; then \
		find $(SCRIPTS_DIR) -name "*.sh" \
			! -path "*/node_modules/*" \
			! -path "*/.venv/*" \
			-exec shfmt -w -i 4 -bn -ci -sr {} + \
			2>&1 || echo "$(YELLOW)shfmt formatting completed with warnings$(NC)"; \
		echo "$(GREEN)Shell formatting complete!$(NC)"; \
	else \
		echo "$(YELLOW)shfmt not found. Install with: go install mvdan.cc/sh/v3/cmd/shfmt@latest$(NC)"; \
		echo "$(YELLOW)Skipping shell formatting...$(NC)"; \
	fi
	@if command -v shellcheck >/dev/null 2>&1; then \
		find $(SCRIPTS_DIR) -name "*.sh" \
			! -path "*/node_modules/*" \
			! -path "*/.venv/*" \
			-exec shellcheck --severity=error {} + \
			2>&1 || echo "$(RED)ShellCheck found errors$(NC)"; \
		echo "$(GREEN)Shell linting complete!$(NC)"; \
	else \
		echo "$(YELLOW)shellcheck not found. Install with: sudo apt-get install shellcheck$(NC)"; \
		echo "$(YELLOW)Skipping shell linting...$(NC)"; \
	fi

lint: lint-python

lint-python:
	@echo "$(CYAN)Linting Python code with ruff...$(NC)"
	@if command -v ruff >/dev/null 2>&1; then \
		ruff check $(SCRIPTS_DIR) $(TESTS_DIR) --quiet || echo "$(RED)Ruff found issues$(NC)"; \
		echo "$(GREEN)Linting complete$(NC)"; \
	else \
		echo "$(RED)Ruff not found. Install with: pip install ruff$(NC)"; \
		exit 1; \
	fi

check: format lint test
	@echo ""
	@echo "$(GREEN)All checks passed!$(NC)"

# ============================================
# Information & Diagnostics
# ============================================
info:
	@echo "$(CYAN)Project Information:$(NC)"
	@echo ""
	@echo "  $(CYAN)Project:$(NC) SciTeX Template Research"
	@echo "  $(CYAN)Python:$(NC) $$($(PYTHON) --version 2>&1)"
	@echo "  $(CYAN)Scripts:$(NC) $$(find $(SCRIPTS_DIR) -name "*.py" | wc -l) Python files"
	@echo "  $(CYAN)Config:$(NC) $$(ls -1 $(CONFIG_DIR)/*.yaml 2>/dev/null | wc -l) YAML files"
	@echo ""
	@echo "  $(CYAN)MNIST Scripts:$(NC)"
	@echo "    - $$(ls -1 $(MNIST_DIR)/*.py 2>/dev/null | wc -l) scripts"
	@echo "    - $$(ls -1d $(MNIST_DIR)/*_out 2>/dev/null | wc -l) output directories"
	@echo ""
	@if [ -d $(DATA_DIR)/mnist/figures ]; then \
		echo "  $(CYAN)Generated Figures:$(NC) $$(ls -1 $(DATA_DIR)/mnist/figures/*.jpg 2>/dev/null | wc -l)"; \
	fi
	@if [ -d $(DATA_DIR)/mnist/models ]; then \
		echo "  $(CYAN)Saved Models:$(NC) $$(ls -1 $(DATA_DIR)/mnist/models/*.pkl 2>/dev/null | wc -l)"; \
	fi

tree:
	@echo "$(CYAN)Project Structure:$(NC)"
	@if command -v tree >/dev/null 2>&1; then \
		tree -L 3 -I '__pycache__|*.pyc|.git|.venv|*.egg-info|.pytest_cache|.ruff_cache|.mypy_cache' -C; \
	else \
		echo "$(YELLOW)tree command not found. Install with: sudo apt-get install tree$(NC)"; \
		ls -R; \
	fi

show-config:
	@echo "$(CYAN)Configuration Files:$(NC)"
	@echo ""
	@if command -v yq >/dev/null 2>&1; then \
		for cfg in $(CONFIG_DIR)/*.yaml; do \
			if [ -f "$$cfg" ]; then \
				echo "$(GREEN)$$cfg:$(NC)"; \
				yq -C '.' "$$cfg" 2>/dev/null || cat "$$cfg"; \
				echo ""; \
			fi; \
		done; \
	else \
		echo "$(YELLOW)yq not installed. Showing raw YAML files:$(NC)"; \
		echo "$(YELLOW)(Install yq for colored output: sudo apt-get install yq or brew install yq)$(NC)"; \
		echo ""; \
		for cfg in $(CONFIG_DIR)/*.yaml; do \
			if [ -f "$$cfg" ]; then \
				echo "$(GREEN)$$cfg:$(NC)"; \
				cat "$$cfg"; \
				echo ""; \
			fi; \
		done; \
	fi

# ============================================
# Utility Targets
# ============================================
.SILENT: help install verify

# EOF
