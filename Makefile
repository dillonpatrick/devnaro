.DEFAULT_GOAL := help

.PHONY: help install build rebuild test config clean

# ==========================================
# Development and maintenance commands
# ==========================================

help: ## Show available commands
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | \
	awk 'BEGIN {FS = ":.*?## "}; {printf "  %-20s %s\n", $$1, $$2}'

install: ## Install the host-side DevBox command
	@bash ./install.sh

build: ## Build DevBox image
	@docker compose build

rebuild: ## Rebuild DevBox image without cache
	@docker compose build --no-cache

test: ## Run Python unit and smoke tests
	@docker compose exec devbox pytest /opt/devbox-cli/tests

config: ## Validate Docker Compose configuration
	@docker compose config --quiet
	@echo "Docker Compose configuration is valid."

clean: ## Remove DevBox containers, networks and volumes
	@docker compose down --volumes --remove-orphans
