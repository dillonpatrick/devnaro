.DEFAULT_GOAL := help

.PHONY: help install build rebuild test config clean

# ==========================================
# Development and maintenance commands
# ==========================================

help: ## Show available commands
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | \
	awk 'BEGIN {FS = ":.*?## "}; {printf "  %-20s %s\n", $1, $$2}'

install: ## Install the host-side devbox command
	@bash ./scripts/host/install.sh

build: ## Build DevBox image
	@bash ./scripts/host/ensure-ports-config.sh
	@docker compose --project-directory . -f docker/docker-compose.yml -f docker/docker-compose.ports.yml build

rebuild: ## Rebuild DevBox image without cache
	@bash ./scripts/host/ensure-ports-config.sh
	@docker compose --project-directory . -f docker/docker-compose.yml -f docker/docker-compose.ports.yml build --no-cache

test: ## Run Python unit tests (DevBox must be running)
	@bash ./scripts/host/ensure-ports-config.sh
	@docker compose --project-directory . -f docker/docker-compose.yml -f docker/docker-compose.ports.yml exec devbox pytest /opt/devbox-cli/tests/unit

config: ## Validate Docker Compose configuration
	@bash ./scripts/host/ensure-ports-config.sh
	@docker compose --project-directory . -f docker/docker-compose.yml -f docker/docker-compose.ports.yml config --quiet
	@echo "Docker Compose configuration is valid."

clean: ## Remove DevBox containers, networks, volumes, and local images
	@bash ./scripts/host/clean.sh
