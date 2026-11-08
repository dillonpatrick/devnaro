.DEFAULT_GOAL := help

.PHONY: help install build rebuild test config clean

# ==========================================
# Development and maintenance commands
# ==========================================

help: ## Show available commands
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | \
	awk 'BEGIN {FS = ":.*?## "}; {printf "  %-20s %s\n", $$1, $$2}'

install: ## Install the host-side DevBox command
	@bash ./scripts/host/install.sh

build: ## Build DevBox image
	@docker compose -f docker/docker-compose.yml build

rebuild: ## Rebuild DevBox image without cache
	@docker compose -f docker/docker-compose.yml build --no-cache

test: ## Run Python unit and smoke tests
	@docker compose -f docker/docker-compose.yml exec devbox pytest /opt/devbox-cli/tests/unit

config: ## Validate Docker Compose configuration
	@docker compose -f docker/docker-compose.yml config --quiet
	@echo "Docker Compose configuration is valid."

clean: ## Remove DevBox containers, networks and volumes
	@docker compose -f docker/docker-compose.yml down --volumes --remove-orphans
