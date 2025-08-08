APP_ENV_FILE=.env

# Default options
service ?= both
env ?= .env
action ?= up
compose ?= compose.yml
execute ?= local
verbose ?= false

help:
	@echo "Usage: make COMMAND [OPTIONS]"
	@echo ""
	@echo "quickstart [action=up|down] [env=.env] [compose=compose.yml]		Start services in docker environment"
	@echo ""
	@echo " action						Optional, 'up' to start services or 'down' to stop services. Default: up"
	@echo " env 						Optional, environment file to use. Default: .env"
	@echo " compose 					Optional, compose file to use. Default: compose.yml"
	@echo ""
	@echo "dev [service=api|playground|both] [env=.env] [compose=compose.yml]	Start services in local development mode"
	@echo ""
	@echo " service 					Optional, start specific service or both. Default: both"
	@echo " env 						Optional, environment file to use. Default: .env"
	@echo " compose 					Optional, compose file to use. Default: compose.yml"
	@echo ""
	@echo "create-user								Create a first user"
	@echo "test									Run unit tests"
	@echo "lint									Run linter"
	@echo ""
	@echo "test-integ [action=up|down|run|all] [execute=local|docker] [verbose=true]	Run integration tests"
	@echo ""
	@echo " action								Optional, 'up' to start services without running tests, 'down' to stop "
	@echo "								services, 'run' to run tests without starting services, 'all' to start"
	@echo "								services and run tests. Default: up"
	@echo " execute							Optional, run integration tests in local or docker environment. Default: local"
	@echo " verbose							Optional, enable verbose output for debugging. Default: false"
	@echo ""

# utils ----------------------------------------------------------------------------------------------------------------------------------------------
.banner:
	@echo ""
	@echo " ██████╗ ██████╗ ███████╗███╗   ██╗ ██████╗  █████╗ ████████╗███████╗██╗     ██╗     ███╗   ███╗"
	@echo "██╔═══██╗██╔══██╗██╔════╝████╗  ██║██╔════╝ ██╔══██╗╚══██╔══╝██╔════╝██║     ██║     ████╗ ████║"
	@echo "██║   ██║██████╔╝█████╗  ██╔██╗ ██║██║  ███╗███████║   ██║   █████╗  ██║     ██║     ██╔████╔██║"
	@echo "██║   ██║██╔═══╝ ██╔══╝  ██║╚██╗██║██║   ██║██╔══██║   ██║   ██╔══╝  ██║     ██║     ██║╚██╔╝██║"
	@echo "╚██████╔╝██║     ███████╗██║ ╚████║╚██████╔╝██║  ██║   ██║   ███████╗███████╗███████╗██║ ╚═╝ ██║"
	@echo " ╚═════╝ ╚═╝     ╚══════╝╚═╝  ╚═══╝ ╚═════╝ ╚═╝  ╚═╝   ╚═╝   ╚══════╝╚══════╝╚══════╝╚═╝     ╚═╝"
	@echo ""

.start:
	@if [ "$(service)" = "api" ]; then \
		$(MAKE) .banner; \
		echo "┌─────────────────────────────────────────────────────────────────┐"; \
		echo "│                        🚀 Services ready                        │"; \
		echo "├─────────────────────────────────────────────────────────────────┤"; \
		echo "│ ▶️  API URL: http://localhost:8080                               │"; \
		echo "│ ⏸️  Press Ctrl+C to stop all services                            │"; \
		echo "└─────────────────────────────────────────────────────────────────┘"; \
		echo ""; \
		bash -c 'set -a; . $(env); GUNICORN_CMD_ARGS="--reload --log-level debug --access-logfile - --error-logfile -" ./scripts/startup_api.sh'; \
		wait; \
	elif [ "$(service)" = "playground" ]; then \
		$(MAKE) .banner; \
		echo "┌─────────────────────────────────────────────────────────────────┐"; \
		echo "│                        🚀 Services ready                        │"; \
		echo "├─────────────────────────────────────────────────────────────────┤"; \
		echo "│ ▶️  Playground URL: http://localhost:8081                        │"; \
		echo "│ ⏸️  Press Ctrl+C to stop all services                            │"; \
		echo "└─────────────────────────────────────────────────────────────────┘"; \
		echo ""; \
		bash -c 'set -a; . $(env); STREAMLIT_CMD_ARGS="--server.port 8081" ./scripts/startup_ui.sh'; \
		wait; \
	elif [ "$(service)" = "both" ]; then \
		$(MAKE) .banner; \
		echo "┌─────────────────────────────────────────────────────────────────┐"; \
		echo "│                        🚀 Services ready                        │"; \
		echo "├─────────────────────────────────────────────────────────────────┤"; \
		echo "│ ▶️  API URL: http://localhost:8080                               │"; \
		echo "│ ▶️  Playground URL: http://localhost:8081                        │"; \
		echo "│ ⏸️  Press Ctrl+C to stop all services                            │"; \
		echo "└─────────────────────────────────────────────────────────────────┘"; \
		echo ""; \
		bash -c 'set -a; . $(env); GUNICORN_CMD_ARGS="--reload --log-level debug --access-logfile - --error-logfile -" ./scripts/startup_api.sh' & \
		bash -c 'set -a; . $(env); STREAMLIT_CMD_ARGS="--server.port 8081" ./scripts/startup_ui.sh' & \
		wait; \
	else \
		echo "❌ Error: service must be 'api' or 'playground' or 'both'"; \
		exit 1; \
	fi

.docker-compose:
	@if [ "$(action)" = "up" ]; then \
		docker compose --env-file $(env) --file $(compose) up $(services) --detach --quiet-pull --wait; \
		echo "✅ Services are ready, waiting for services to be fully initialized..."; \
		sleep 4; \
	elif [ "$(action)" = "down" ]; then \
		docker compose --env-file $(env) --file $(compose) down; \
	fi
	

.check-service-status:
	@echo "🐳 Checking if $(service) container is running..."; \
	status=$$(docker compose -f $(compose) --env-file $(env) ps -a $(service) --format "table {{.State}}" | tail -n +2); \
	if [ "$$status" != "running" ]; then \
		echo "❌ $(service) container is not running (status: $$status). Please check the logs of the container"; \
		false; \
	else \
		echo "✅ $(service) container is running"; \
	fi

# dev ------------------------------------------------------------------------------------------------------------------------------------------------
dev:
	@# Pre-checks
	@if [ ! -f $(env) ]; then \
		echo "❌ Error: Environment file $(env) does not exist"; \
		echo "Use 'make help' for more information."; \
		exit 1; \
	fi

	@bash -c 'set -a; . $(env); \
	if [ ! -f "$$CONFIG_FILE" ]; then \
		echo "🔄 Creating $$CONFIG_FILE file from config.example.yml and using it"; \
		cp config.example.yml "$$CONFIG_FILE"; \
	fi'

	@# Start services
	@services=$$(docker compose --file $(compose) config --services | grep -v -E '^(api|playground)$$' | tr '\n' ' '); \
	echo "🔄 Starting services: $$services"; \
	echo "🚀 Starting services with $(env) file and $(compose) file"; \
	if [ "$(service)" = "api" ]; then \
		trap 'echo "🛑 Stopping all services..."; kill $$(jobs -p) 2>/dev/null; $(MAKE) .docker-compose env=$(env) compose=$(compose) action=down; exit' INT TERM; \
		$(MAKE) .docker-compose env=$(env) compose=$(compose) action=up services="$$services"; \
		echo "✅ Starting API..."; \
		$(MAKE) .start service=api env=$(env); \
	elif [ "$(service)" = "playground" ]; then \
		trap 'echo "🛑 Stopping all services..."; kill $$(jobs -p) 2>/dev/null; $(MAKE) .docker-compose env=$(env) compose=$(compose) action=down; exit' INT TERM; \
		$(MAKE) .docker-compose env=$(env) compose=$(compose) action=up services="$$services"; \
		echo "✅ Starting playground..."; \
		$(MAKE) .start service=playground env=$(env); \
	elif [ "$(service)" = "both" ]; then \
		trap 'echo "🛑 Stopping all services..."; kill $$(jobs -p) 2>/dev/null; $(MAKE) .docker-compose env=$(env) compose=$(compose) action=down; exit' INT TERM; \
		$(MAKE) .docker-compose env=$(env) compose=$(compose) action=up services="$$services"; \
		echo "✅ Starting API and Playground..."; \
		$(MAKE) .start service=both env=$(env); \
	else \
		echo "❌ Error: service must be 'api' or 'playground'"; \
		echo "Usage: make dev service=api|playground env=.env"; \
		echo "Use 'make help' for more information."; \
		exit 1; \
	fi

# quickstart -----------------------------------------------------------------------------------------------------------------------------------------
quickstart:
	@# Pre-checks
	@if [ ! -f $(env) ]; then \
		echo "🔄 Creating $(env) file from $(env).example and using it"; \
		cp $(env).example $(env); \
	fi

	@bash -c 'set -a; . $(env); \
	if [ ! -f "$$CONFIG_FILE" ]; then \
		echo "🔄 Creating $$CONFIG_FILE file from config.example.yml and using it"; \
		cp config.example.yml "$$CONFIG_FILE"; \
	fi'

	@# Start services
	@echo "🚀 Starting services with $(env) file and $(compose) file"; \
	if [ "$(action)" = "up" ]; then \
		$(MAKE) .docker-compose env=$(env) compose=$(compose) action=up; \
		if $(MAKE) --silent .check-service-status service=api env=$(env) compose=$(compose) && $(MAKE) --silent .check-service-status service=playground env=$(env) compose=$(compose); then \
			$(MAKE) .banner; \
			echo "┌─────────────────────────────────────────────────────────────────┐"; \
			echo "│                        🚀 Services ready                        │"; \
			echo "├─────────────────────────────────────────────────────────────────┤"; \
			echo "│ ▶️  API URL: http://localhost:8080                               │"; \
			echo "│ ▶️  Playground URL: http://localhost:8081                        │"; \
			echo "│ ⏸️  Execute 'make quickstart action=down' to stop services       │"; \
			echo "└─────────────────────────────────────────────────────────────────┘"; \
			echo ""; \
		fi; \
	elif [ "$(action)" = "down" ]; then \
		$(MAKE) .docker-compose env=$(env) compose=$(compose) action=down; \
	else \
		echo "❌ Error: action must be 'up' or 'down'"; \
		echo "Usage: make quickstart action=up|down"; \
		echo "Use 'make help' for more information."; \
		exit 1; \
	fi

# test -----------------------------------------------------------------------------------------------------------------------------------------------
test:
	PYTHONPATH=. pytest app/tests/unit --config-file=pyproject.toml

# lint -----------------------------------------------------------------------------------------------------------------------------------------------
lint:
	pre-commit run --all-files

# create-user ----------------------------------------------------------------------------------------------------------------------------------------
create-user:
	docker compose exec -ti api python scripts/create_first_user.py --playground_postgres_host postgres

# test-integ -----------------------------------------------------------------------------------------------------------------------------------------
.test-integ-up:
	@if [ ! -f .github/.env.ci ]; then \
		echo "🔄 Creating .github/.env.ci file from .github/.env.ci.example and using it"; \
		cp .github/.env.ci.example .github/.env.ci; \
	fi

	@bash -c 'set -a; . .github/.env.ci; \
	if [ -z "$$ALBERT_API_KEY" ]; then \
		echo "❌ ALBERT_API_KEY in .github/.env.ci in order to run the integration tests"; \
	fi; \
	if [ -z "$$BRAVE_API_KEY" ]; then \
		echo "❌ BRAVE_API_KEY in .github/.env.ci in order to run the integration tests"; \
	fi'
	@if [ "$(execute)" = "local" ]; then \
		bash -c 'set -a; . .github/.env.ci; \
		if [ $$POSTGRES_HOST != "localhost" ]; then \
			echo "❌ POSTGRES_HOST must be set to 'localhost' in order to run the integration tests local execute"; \
			exit 1; \
		fi; \
		if [ $$REDIS_HOST != "localhost" ]; then \
			echo "❌ REDIS_HOST must be set to 'localhost' in order to run the integration tests local execute"; \
			exit 1; \
		fi; \
		if [ $$ELASTICSEARCH_HOST != "localhost" ]; then \
			echo "❌ ELASTICSEARCH_HOST must be set to 'localhost' in order to run the integration tests local execute"; \
			exit 1; \
		fi; \
		if [ $$SECRETIVESHELL_HOST != "localhost" ]; then \
			echo "❌ SECRETIVESHELL_HOST must be set to 'localhost' in order to run the integration tests local execute"; \
			exit 1; \
		fi' && \
		services=$$(docker compose --file .github/compose.ci.yml config --services | grep -v -E '^(api|playground)$$' | tr '\n' ' '); \
		$(MAKE) .docker-compose env=.github/.env.ci compose=.github/compose.ci.yml action=up services="$$services"; \
	elif [ "$(execute)" = "docker" ]; then \
		bash -c 'set -a; . .github/.env.ci; \
		if [ $$POSTGRES_HOST != "postgres" ]; then \
			echo "❌ POSTGRES_HOST must be set to 'postgres' in order to run the integration tests in docker execute"; \
			exit 1; \
		fi; \
		if [ $$REDIS_HOST != "redis" ]; then \
			echo "❌ REDIS_HOST must be set to 'redis' in order to run the integration tests in docker execute"; \
			exit 1; \
		fi; \
		if [ $$ELASTICSEARCH_HOST != "elasticsearch" ]; then \
			echo "❌ ELASTICSEARCH_HOST must be set to 'elasticsearch' in order to run the integration tests in docker execute"; \
			exit 1; \
		fi; \
		if [ $$SECRETIVESHELL_HOST != "secretiveshell" ]; then \
			echo "❌ SECRETIVESHELL_HOST must be set to 'secretiveshell' in order to run the integration tests in docker execute"; \
			exit 1; \
		fi; \
		if [ $$POSTGRES_PORT != "5432" ]; then \
			echo "❌ POSTGRES_PORT must be set to '5432' in order to run the integration tests in docker execute"; \
			exit 1; \
		fi; \
		if [ $$REDIS_PORT != "6379" ]; then \
			echo "❌ REDIS_PORT must be set to '6379' in order to run the integration tests in docker execute"; \
			exit 1; \
		fi; \
		if [ $$ELASTICSEARCH_PORT != "9200" ]; then \
			echo "❌ ELASTICSEARCH_PORT must be set to '9200' in order to run the integration tests in docker execute"; \
			exit 1; \
		fi; \
		if [ $$SECRETIVESHELL_PORT != "8000" ]; then \
			echo "❌ SECRETIVESHELL_PORT must be set to '8000' in order to run the integration tests in docker execute"; \
			exit 1; \
		fi' && \
		$(MAKE) .docker-compose env=.github/.env.ci compose=.github/compose.ci.yml action=up; \
	else \
		echo "❌ Error: execute must be 'local' or 'docker'"; \
		echo "Usage: make .test-integ-env execute=local|docker"; \
		exit 1; \
	fi

.test-integ-run:
	@if [ "$(execute)" = "local" ]; then \
		bash -c 'set -a; . .github/.env.ci; \
		CONFIG_FILE=app/tests/integ/config.test.yml PYTHONPATH=. pytest app/tests/integ --config-file=pyproject.toml'; \
	elif [ "$(execute)" = "docker" ]; then \
		if $(MAKE) --silent .check-service-status service=api env=.github/.env.ci compose=.github/compose.ci.yml; then \
			docker compose --file .github/compose.ci.yml --env-file .github/.env.ci exec -T api pytest app/tests --cov=./app --cov-report=xml; \
		else \
			echo "❌ API container is not ready, cannot run tests."; \
			exit 1; \
		fi; \
	else \
		echo "❌ Error: execute must be 'local' or 'docker'"; \
		echo "Usage: make .test-integ-run execute=local|docker"; \
		exit 1; \
	fi

test-integ:
	@if [ "$(execute)" != "local" ] && [ "$(execute)" != "docker" ]; then \
		echo "❌ Error: execute must be 'local' or 'docker'"; \
		echo "Usage: make test-integ [action=up|down|run|all] [execute=local|docker]"; \
		echo "Use 'make help' for more information."; \
		exit 1; \
	fi

	@if [ "$(action)" = "all" ]; then \
		if $(MAKE) .test-integ-up execute=$(execute); then \
			$(MAKE) .test-integ-run execute=$(execute); \
		fi; \
	elif [ "$(action)" = "up" ]; then \
		$(MAKE) .test-integ-up execute=$(execute); \
		echo "✅ Environment setup completed: run tests with 'make test-integ action=run execute=$(execute)'"; \
	elif [ "$(action)" = "down" ]; then \
		docker compose -f .github/compose.ci.yml --env-file .github/.env.ci down; \
		echo "✅ Environment shutdown completed."; \
	elif [ "$(action)" = "run" ]; then \
		$(MAKE) .test-integ-run execute=$(execute); \
		echo "✅ Integration tests completed."; \
	else \
		echo "❌ Error: action must be 'up', 'down', 'run', or 'all'"; \
		echo "Usage: make test-integ [action=up|down|run|all] [execute=local|docker] [verbose=true]"; \
		echo "Use 'make help' for more information."; \
		exit 1; \
	fi

.PHONY: help test test-integ lint setup quickstart dev
