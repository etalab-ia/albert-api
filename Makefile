CONFIG_FILE=./config.yml
PYPROJECT=pyproject.toml

APP_ENV_FILE=.env
TEST_ENV_FILE=.env.test

install:
	pip install ".[app,ui,dev,test]"

docker-compose-up:
	docker compose --env-file ${APP_ENV_FILE} up --detach

docker-compose-down:
	docker compose --env-file ${APP_ENV_FILE} down

docker-compose-test-up:
	docker compose --env-file ${TEST_ENV_FILE} up --detach

docker-compose-test-down:
	docker compose --env-file ${TEST_ENV_FILE} down

run-api:
	uvicorn app.main:app --port 8000 --log-level debug --reload

run-ui:
	streamlit run ui/main.py --server.port 8501 --theme.base light

db-app-migrate:
	alembic -c app/alembic.ini upgrade head

db-test-migrate:
	ENV_FILE=${TEST_ENV_FILE} alembic -c app/alembic.ini upgrade head

db-ui-migrate:
	alembic -c ui/alembic.ini upgrade head

test-all:
	CONFIG_FILE=$(CONFIG_FILE) ENV_FILE=${TEST_ENV_FILE} PYTHONPATH=. pytest --config-file=$(PYPROJECT)

test-unit:
	CONFIG_FILE=$(CONFIG_FILE) PYTHONPATH=. pytest app/tests/unit --config-file=$(PYPROJECT)

test-integ:
	CONFIG_FILE=$(CONFIG_FILE) ENV_FILE=${TEST_ENV_FILE} PYTHONPATH=. pytest app/tests/integ--config-file=$(PYPROJECT)

test-snap-update:
	CONFIG_FILE=$(CONFIG_FILE) PYTHONPATH=. pytest --config-file=$(PYPROJECT) --snapshot-update

install-lint:
	pre-commit install

lint:
	pre-commit run --all-files

.PHONY: run-api run-ui db-app-migrate db-ui-migrate test-all test-unit test-integ test-snap-update lint