.DEFAULT_GOAL := help

.PHONY: help install uninstall build rebuild test config clean

# ==========================================
# Development and maintenance commands
# ==========================================

help: ## Show available commands
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | \
	awk 'BEGIN {FS = ":.*?## "}; {printf "  %-20s %s\n", $1, $$2}'

install: ## Install the host-side devnaro command
	@sudo -k && sudo -v
	@bash ./scripts/host/install.sh

build: ## Build DevNaro image
	@bash ./scripts/host/compose.sh build

rebuild: ## Rebuild DevNaro image without cache
	@bash ./scripts/host/compose.sh build --no-cache

test: ## Run Python unit tests (DevNaro must be running)
	@bash ./scripts/host/compose.sh exec devnaro pytest /opt/devnaro-cli/tests/unit

config: ## Validate Docker Compose configuration
	@bash ./scripts/host/compose.sh config --quiet
	@echo "Docker Compose configuration is valid."

clean: ## Remove DevNaro containers, networks, volumes, and local images
	@bash ./scripts/host/clean.sh

uninstall: ## Completely remove DevNaro while preserving the workspace
	@sudo -k && sudo -v
	@bash ./scripts/host/uninstall.sh
