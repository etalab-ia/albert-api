CONFIG_FILE=./config.yml
CONFIG_TEST_FILE=app/tests/config.test.yml
PYPROJECT=pyproject.toml

APP_ENV_FILE=.env
TEST_ENV_FILE=.env.test
QUICKSTART_ENV_FILE=.env.example

env_file ?= .env
external_services="postgres redis elasticsearch mcp-bridge"
quickstart_services="api playground postgres redis"
ci_services="api postgres redis elasticsearch mcp-bridge"

docker-compose-quickstart-up:
	@$(MAKE) --silent .docker-compose-up env_file=$(QUICKSTART_ENV_FILE) services=$(quickstart_services)
	@echo "API URL: http://localhost:8080"
	@echo "Playground URL: http://localhost:8501"

docker-compose-quickstart-down:
	@$(MAKE) --silent .docker-compose-down env_file=$(QUICKSTART_ENV_FILE)

docker-compose-albert-api-up:
	@$(MAKE) --silent .docker-compose-up env_file=$(APP_ENV_FILE)

docker-compose-albert-api-down env-services-down:
	@$(MAKE) --silent .docker-compose-down env_file=$(APP_ENV_FILE)

env-services-up:
	@$(MAKE) --silent docker-compose-albert-api-up services=$(external_services)

env-test-services-up:
	@$(MAKE) --silent .docker-compose-up env_file=$(TEST_ENV_FILE) services=$(external_services)

env-test-services-down:
	@$(MAKE) --silent .docker-compose-down env_file=$(TEST_ENV_FILE)

.docker-compose-up:
	docker compose --env-file $(env_file) up $(services) --detach

.docker-compose-down:
	docker compose --env-file $(env_file) down

env-ci-up:
	@if [ ! -f .github/.env.ci ]; then \
		cp .env.example .github/.env.ci; \
		sed -i 's/CONFIG_FILE=.*/CONFIG_FILE=app\/tests\/config.test.yml/' .github/.env.ci; \
		sed -i 's/COMPOSE_PROJECT_NAME=.*/COMPOSE_PROJECT_NAME=albert-api-ci/' .github/.env.ci; \
	fi
	docker compose -f .github/compose.ci.yml --env-file .github/.env.ci up --detach

env-ci-down:
	docker compose -f .github/compose.ci.yml --env-file .github/.env.ci down

install:
	pip install ".[app,ui,dev,test]"

configuration:
	python scripts/generate_models_configuration.py

install-lint:
	pre-commit install

lint:
	pre-commit run --all-files

run-api:
	bash -c 'set -a; . $(APP_ENV_FILE); ./scripts/startup_api.sh'

run-ui:
	bash -c 'set -a; . $(APP_ENV_FILE); ./scripts/startup_ui.sh'

db-app-migrate:
	bash -c 'set -a; . $(APP_ENV_FILE); alembic -c app/alembic.ini upgrade head'

db-test-migrate:
	bash -c 'set -a; . $(TEST_ENV_FILE); alembic -c app/alembic.ini upgrade head'

db-ui-migrate:
	bash -c 'set -a; . $(APP_ENV_FILE); alembic -c ui/alembic.ini upgrade head'

test-all:
	bash -c 'set -a; . $(TEST_ENV_FILE); CONFIG_FILE=$(CONFIG_TEST_FILE) PYTHONPATH=. pytest --config-file=$(PYPROJECT)'

test-unit:
	bash -c 'set -a; . $(TEST_ENV_FILE); CONFIG_FILE=$(CONFIG_TEST_FILE) PYTHONPATH=. pytest app/tests/unit --config-file=$(PYPROJECT)'

test-integ:
	bash -c 'set -a; . $(TEST_ENV_FILE); CONFIG_FILE=$(CONFIG_TEST_FILE) PYTHONPATH=. pytest app/tests/integ--config-file=$(PYPROJECT)'

test-ci:
	docker exec albert-api-ci-api-1 pytest app/tests --cov=./app --cov-report=xml

setup: install configuration install-lint env-services-up db-app-migrate db-ui-migrate

.PHONY: run-api run-ui db-app-migrate db-ui-migrate test-all test-unit test-integ lint setup docker-compose-albert-api-up docker-compose-albert-api-down env-services-down env-services-up env-test-services-up env-test-services-down quickstart-up quickstart-down env-ci-up env-ci-down