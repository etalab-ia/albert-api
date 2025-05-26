# Contributing

To contribute to the project, please follow the instructions below.

## Development in Docker environment

> **⚠️ Warning**<br>
> You must have access to a language model API.

1. Create a *config.yml* file based on the example configuration file *[config.example.yml](./config.example.yml)* with your models.

    For more information on deploying services, please consult the [dedicated documentation](./docs/deployment.md).

    > **❗️Note**<br>
    > The configuration file for running tests is [config.test.yml](./.github/config.test.yml). You can use it as inspiration to configure your own configuration file.

2. Launch the development docker compose with watch mode:

    ```bash
    docker compose --file compose.dev.yml up --watch
    ```

    > **❗️Note**<br>
    > The API and playground will be available on ports 8000 and 8501 respectively. To connect to the playground for the first time, use the login *master* and password *changeme* (defined in the configuration file).

## Development outside Docker environment

1. Create a *config.yml* file based on the example configuration file *[config.example.yml](./config.example.yml)* with your models.

    For more information on deploying services, please consult the [dedicated documentation](./docs/deployment.md).

    > **❗️Note**<br>
    > The configuration file for running tests is [config.test.yml](./.github/config.test.yml). You can use it as inspiration to configure your own configuration file.

2. Set up dependencies

    ```bash
    docker compose up --detach # run the databases

    pip install ".[app,ui,dev,test]" # install the dependencies

    alembic -c app/alembic.ini upgrade head # create the API tables
    alembic -c ui/alembic.ini upgrade head # create the Playground tables
    ```

3. Launch the API

    ```bash
    uvicorn app.main:app --port 8000 --log-level debug --reload
    ```

4. Launch the playground

    In another terminal, launch the playground with the following command:

    ```bash
    streamlit run ui/main.py --server.port 8501 --theme.base light
    ```

    To connect to the playground for the first time, use the login *master* and password *changeme* (defined in the configuration file).

## Modifications to SQL database structure

### Modifications to the [`app/sql/models.py`](./app/sql/models.py) file

If you have modified the API database tables in the [models.py](./app/sql/models.py) file, you need to create an Alembic migration with the following command:

```bash
alembic -c app/alembic.ini revision --autogenerate -m "message"
```

Then apply the migration with the following command:

```bash
alembic -c app/alembic.ini upgrade head
```

### Modifications to the [`ui/sql/models.py`](./ui/sql/models.py) file

If you have modified the UI database tables in the [models.py](./ui/sql/models.py) file, you need to create an Alembic migration with the following command:

```bash
alembic -c ui/alembic.ini revision --autogenerate -m "message"
```

Then apply the migration with the following command:

```bash
alembic -c ui/alembic.ini upgrade head
```

## Tests

> **❗️Note**<br>
> The configuration file for running tests is [config.test.yml](./.github/config.test.yml). You can modify it to run the tests on your machine.
> You need set `$BRAVE_API_KEY` and `$ALBERT_API_KEY` environment variables to run the tests.

### In Docker environment

```bash
docker compose --file ./.github/compose.test.yml up --detach
docker exec -it albert-test-api-1 pytest app/tests
```

### Outside Docker environment

1. Run the databases services and export environment variables

    ```bash 
    docker compose --file .github/compose.test.yml up postgres qdrant redis --detach

    export POSTGRES_HOST=localhost
    export REDIS_HOST=localhost
    export QDRANT_HOST=localhost
    export POSTGRES_PORT=8432
    export REDIS_PORT=8335
    export QDRANT_PORT=8333
    export QDRANT_GRPC_PORT=8334
    ```

2. Run the tests

    ```bash
    CONFIG_FILE=./.github/config.test.yml PYTHONPATH=. pytest --config-file=pyproject.toml
    ```

    To update the snapshots, run the following command:

    ```bash
    CONFIG_FILE=./.github/config.test.yml PYTHONPATH=. pytest --config-file=pyproject.toml --snapshot-update
    ```

## Notebooks

It is important to keep the notebooks in the docs/tutorials folder up to date, to show quick examples of API usage.

To launch the notebooks locally:

```bash
pip install ".[dev]"
jupyter notebook docs/tutorials/
```

## Linter

The project linter is [Ruff](https://beta.ruff.rs/docs/configuration/). The specific project formatting rules are in the *[pyproject.toml](./pyproject.toml)* file.

Please install the pre-commit hooks:

```bash
pip install ".[dev]"
pre-commit install
```

Ruff will run automatically at each commit.

## Commit

Please respect the following convention for your commits:

```
[doc|feat|fix](theme) commit object (in english)

# example
feat(collections): collection name retriever
```
