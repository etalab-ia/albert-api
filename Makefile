CONFIG_FILE=./config.yml
CONFIG_TEST_FILE=app/tests/integ/config.test.yml
PYPROJECT=pyproject.toml

APP_ENV_FILE=.env
TEST_ENV_FILE=.env.test
QUICKSTART_ENV_FILE=.env.example

env_file ?= .env
external_services="postgres redis elasticsearch secretiveshell"
quickstart_services="api postgres redis playground"
ci_services="api postgres redis elasticsearch secretiveshell"

quickstart:
	@if [ ! -f config.yml ]; then cp config.example.yml config.yml; fi
	@if [ ! -f .env ]; then cp .env.example .env; fi
	@$(MAKE) --silent .docker-compose-up env_file=$(APP_ENV_FILE) services=$(quickstart_services)
	@echo "API URL: http://localhost:8080"
	@echo "API token: changeme"
	@echo "Playground URL: http://localhost:8081/playground"
	@echo "Playground user: master"
	@echo "Playground password: changeme"


quickstart-down:
	@$(MAKE) --silent .docker-compose-down env_file=$(APP_ENV_FILE)

docker-compose-opengatellm-up:
	@$(MAKE) --silent .docker-compose-up env_file=$(APP_ENV_FILE)

docker-compose-opengatellm-down env-services-down:
	@$(MAKE) --silent .docker-compose-down env_file=$(APP_ENV_FILE)

env-services-up:
	@$(MAKE) --silent docker-compose-opengatellm-up services=$(external_services)

env-test-services-up:
	@$(MAKE) --silent .docker-compose-up env_file=$(TEST_ENV_FILE) services=$(external_services)

.docker-compose-up:
	docker compose --env-file $(env_file) up $(services) --detach

.docker-compose-down:
	docker compose --env-file $(env_file) down

env-ci-up:
	@SED_INPLACE=$$(if [ "$$(uname)" = "Darwin" ]; then echo "sed -i ''"; else echo "sed -i"; fi); \
	@if [ ! -f .github/.env.ci ]; then \
		cp .env.example .github/.env.ci; \
		$$SED_INPLACE 's/CONFIG_FILE=.*/CONFIG_FILE=app\/tests\/integ\/config.test.yml/' .github/.env.ci; \
		$$SED_INPLACE 's/COMPOSE_PROJECT_NAME=.*/COMPOSE_PROJECT_NAME=opengatellm-ci/' .github/.env.ci; \
	fi
	docker compose -f .github/compose.ci.yml --env-file .github/.env.ci up --build --force-recreate --detach

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
	PYTHONPATH=. pytest app/tests/unit --config-file=$(PYPROJECT)

test-integ:
	bash -c 'set -a; . $(TEST_ENV_FILE); CONFIG_FILE=$(CONFIG_TEST_FILE) PYTHONPATH=. pytest app/tests/integ--config-file=$(PYPROJECT)'

test-ci:
	docker compose -f .github/compose.ci.yml --env-file .github/.env.ci exec -ti api pytest app/tests --cov=./app --cov-report=xml

create-user:
	docker compose exec -ti api python scripts/create_first_user.py --playground_postgres_host postgres

setup: install configuration install-lint env-services-up db-app-migrate db-ui-migrate

.PHONY: run-api run-ui db-app-migrate db-ui-migrate test-all test-unit test-integ lint setup docker-compose-opengatellm-up docker-compose-opengatellm-down env-services-down env-services-up env-test-services-up env-test-services-down quickstart env-ci-up env-ci-down
