ifneq (,$(wildcard .env))
	include .env
	export
endif


CONFIG_FILE=./config.yml
PYPROJECT=pyproject.toml

install:
	pip install ".[app,ui,dev,test]"

docker-compose:
	docker compose up --detach

docker-compose-test:
	bash -c 'set -a; . .env.test; exec docker compose --env-file .env.test up --detach'

docker-compose-test-2:
	sh -c 'set -a; . .env'

run-api:
	uvicorn app.main:app --port 8000 --log-level debug --reload

run-ui:
	streamlit run ui/main.py --server.port 8501 --theme.base light

db-app-migrate:
	alembic -c app/alembic.ini upgrade head

db-ui-migrate:
	alembic -c ui/alembic.ini upgrade head

test-all:
	CONFIG_FILE=$(CONFIG_FILE) PYTHONPATH=. pytest --config-file=$(PYPROJECT)

test-unit:
	CONFIG_FILE=$(CONFIG_FILE) PYTHONPATH=. pytest app/tests/unit --config-file=$(PYPROJECT)

test-integ:
	CONFIG_FILE=$(CONFIG_FILE) PYTHONPATH=. pytest app/tests/integ --config-file=$(PYPROJECT)

test-snap-update:
	CONFIG_FILE=$(CONFIG_FILE) PYTHONPATH=. pytest --config-file=$(PYPROJECT) --snapshot-update

install-lint:
	pre-commit install

lint:
	pre-commit run --all-files

.PHONY: run-api run-ui db-app-migrate db-ui-migrate test-all test-unit test-integ test-snap-update lint