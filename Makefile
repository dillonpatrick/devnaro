.DEFAULT_GOAL := help

.PHONY: help start stop restart build rebuild status logs logs-follow shell manager-logs ps networks config clean doctor cli-status cli-networks manager-status

# ==========================================
# Main commands
# ==========================================

help: ## Show available commands
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | \
	awk 'BEGIN {FS = ":.*?## "}; {printf "  %-20s %s\\n", $$1, $$2}'

start: ## Start DevBox using start.sh
	@./start.sh

stop: ## Stop and remove DevBox resources
	@./stop.sh

restart: stop start ## Restart DevBox

# ==========================================
# Build commands
# ==========================================

build: ## Build DevBox image
	@docker compose build

rebuild: ## Rebuild DevBox image without cache
	@docker compose build --no-cache

# ==========================================
# Container commands
# ==========================================

status: ## Show DevBox container status
	@docker compose ps devbox

ps: ## List running Docker containers
	@docker ps

shell: ## Open a shell inside DevBox
	@docker compose exec devbox zsh

# ==========================================
# Python CLI
# ==========================================

doctor: ## Run DevBox health checks
	@docker compose exec devbox devbox-manager doctor

cli-status: ## Show detailed DevBox status using Rich
	@docker compose exec devbox devbox-manager status

cli-networks: ## Show networks connected to DevBox
	@docker compose exec devbox devbox-manager networks

manager-status: ## Show Network Manager process status
	@docker compose exec devbox devbox-manager network-manager status

manager-logs: ## Show Network Manager logs using Rich
	@docker compose exec devbox devbox-manager network-manager logs

# ==========================================
# Logs
# ==========================================

logs: ## Show DevBox container logs
	@docker compose logs devbox

logs-follow: ## Follow DevBox container logs
	@docker compose logs -f devbox

# ==========================================
# Network commands
# ==========================================

networks: ## List Docker networks
	@docker network ls

# ==========================================
# Configuration
# ==========================================

config: ## Validate Docker Compose configuration
	@docker compose config --quiet
	@echo "Docker Compose configuration is valid."

# ==========================================
# Cleanup
# ==========================================

clean: ## Remove DevBox containers, networks and volumes
	@docker compose down --volumes --remove-orphans
