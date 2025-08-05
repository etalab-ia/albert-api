# Contributing

To contribute to the project, please follow the instructions below.

## Development environment

It is recommended to use a Python [virtualenv](https://docs.python.org/3/library/venv.html).

1. Create a _config.yml_ file based on the example configuration file _[config.example.yml](./config.example.yml)_. You can use the default testbed model or configure your own models.

```bash
cp config.example.yml config.yml
cp .env.example .env
```

Check the [configuration documentation](configuration.md) to configure your configuration file.

**❗️Note**
The configuration file for running tests is [config.test.yml](app/tests/integ/config.test.yml). You can use it as inspiration to configure your own configuration file.

2. Set hosts as localhost as we will be running everything locally for dev purposes
   <details>
   <summary> Linux </summary>

   ```bash
   sed -i 's/^\([A-Z_]*_HOST\)=.*/\1=localhost/' .env
   ```

   </details>

   <details>
   <summary> MacOs</summary>

   ```bash
   sed -i '' 's/^\([A-Z_]*_HOST\)=.*/\1=localhost/' .env
   ```

   </details>

   > If you need to revert your changes:
   >
   > <details>
   > <summary> Linux </summary>
   >
   > ```bash
   > sed -i 's/^\([A-Z_]*\)_HOST=localhost/\1_HOST=\L\1/' .env
   > ```
   >
   > </details>
   >
   > <details>
   > <summary> MacOs</summary>
   >
   > ```bash
   > sed -i '' 's/^\([A-Z_]*\)_HOST=localhost/\1_HOST=\L\1/' .env
   > ```
   >
   > </details>

3. Set up dependencies

   ```bash
   docker compose --env-file .env up postgres redis elasticsearch secretiveshell --detach

   pip install ".[app,ui,dev,test]" # install the dependencies

   alembic -c app/alembic.ini upgrade head # create the API tables
   alembic -c ui/alembic.ini upgrade head # create the Playground tables
   ```

   ⚠️ **Warning :** If you ran the make quickstart before, remove all existing containers

   ```bash
   docker compose down api playground
   ```

4. Launch the API

   ```bash
   uvicorn app.main:app --port 8080 --log-level debug --reload
   ```

5. Launch the playground

   In another terminal, launch the playground with the following command:

   ```bash
   streamlit run ui/main.py --server.port 8501 --theme.base light
   ```

   To connect to the playground for the first time, use the login _master_ and password _changeme_ (defined in the configuration file).

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

### In Docker environment

1. Launch the ci environment:
   <details>
   <summary> Linux </summary>

   ```bash
   make env-ci-up
   ```

   </details>

   <details>
   <summary> MacOs</summary>

   ```bash
   make env-ci-up-macos
   ```

   </details>

2. Run the tests:
   ```bash
   docker exec opengatellm-ci-api-1 pytest app/tests --cov=./app --cov-report=xml
   ```

> **❗️Note**
> It will create a .github/.env.ci file.
> The configuration file for running tests is [config.test.yml](app/tests/integ/config.test.yml). You can modify it to run the tests on your machine.
> You need set `$BRAVE_API_KEY` and `$ALBERT_API_KEY` environment variables in `.github/.env.ci` to run the tests.

### Outside Docker environment

1. Create a `.env.test` file and run the databases services:

   ```bash
   cp .env.example .env.test
   make env-test-services-up
   ```

2. Set the HOST variables to localhost:

   <details>
   <summary> Linux </summary>

   ```bash
   sed -i 's/^\([A-Z_]*_HOST\)=.*/\1=localhost/' .env
   ```

   </details>

   <details>
   <summary> MacOs</summary>

   ```bash
   sed -i '' 's/^\([A-Z_]*_HOST\)=.*/\1=localhost/' .env
   ```

   </details>

3. Install the python packages:

   ```bash
   make install
   ```

4. To run the unit and integration tests together:

   ```bash
   make test-all
   ```

5. To run the unit tests:

   ```bash
   make test-unit
   ```

6. To run the integration tests:

   ```bash
   make test-integ
   ```

7. To update the snapshots, run the following command:

   ```bash
   CONFIG_FILE=./.github/config.test.yml PYTHONPATH=. pytest --config-file=pyproject.toml --snapshot-update
   ```

If you want integration tests to use mocked responses, you need to enable VCR by adding to your .env file:

```
VCR_ENABLED=true
```

When you run the integration tests, it will store responses from databases, apis into the app/test/integ/cassettes folder and use them when you rerun the tests

## Notebooks

It is important to keep the notebooks in the docs/tutorials folder up to date, to show quick examples of API usage.

To launch the notebooks locally:

```bash
pip install ".[dev]"
jupyter notebook docs/tutorials/
```

## Linter

The project linter is [Ruff](https://beta.ruff.rs/docs/configuration/). The specific project formatting rules are in the _[pyproject.toml](./pyproject.toml)_ file.

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

And modify the `models` section in the `config.yml` file:

The API keys can be defined directement in the `config.yml` file or in a `.env` file

```bash
cp .env.test.example .env.test

echo 'ALBERT_API_KEY=my_albert_api_key' >> .env.test
echo 'OPENAI_API_KEY=my_openai_api_key' >> .env.test
```

Finally, run the application:

```bash
make docker-compose-opengatellm-up
```

To stop the application, run:

```bash
make docker-compose-opengatellm-down
```

## Running locally

### Prerequisites

- Python 3.8+
- Docker and Docker Compose

### Installation

#### 1. Installing dependencies

```bash
make install
```

#### 2. Configuration

OpenGateLLM supports OpenAI and OpenGateLLM models, defined in the `config.yml` file :

```bash
cp  config.example.yml config.yml
```

And modify the `models` section in the `config.yml` file:

```yaml
models:
  - id: albert-large
    type: text-generation
    owned_by: test
    aliases: ['mistralai/Mistral-Small-3.1-24B-Instruct-2503']
    clients:
      - model: mistralai/Mistral-Small-3.1-24B-Instruct-2503
        type: albert
        args:
          api_url: ${ALBERT_API_URL:-https://albert.api.etalab.gouv.fr}
          api_key: ${ALBERT_API_KEY}
          timeout: 120
  - id: my-language-model
    type: text-generation
    clients:
      - model: gpt-3.5-turbo
        type: openai
        params:
          total: 70
          active: 70
          zone: WOR
        args:
          api_url: https://api.openai.com
          api_key: ${OPENAI_API_KEY}
          timeout: 60
```

The API keys can be defined directement in the `config.yml` file or in a `.env` file

```bash
cp .env.example .env

echo 'ALBERT_API_KEY=my_albert_api_key' >> .env
echo 'OPENAI_API_KEY=my_openai_api_key' >> .env
```

### Running

#### Option 1: Full launch with Docker

```bash
# Start all services (API, playground and external services)
make docker-compose-opengatellm-up
# Stop all services
make docker-compose-opengatellm-down
```

#### Option 2: Local development

Update all the `_HOST` variables in `.env` file:

```bash
sed -i 's/^\([A-Z_]*_HOST\)=.*/\1=localhost/' .env
```

Then, run the following commands:

```bash
# 1. Start only external services (Redis, Qdrant, PostgreSQL, MCP Bridge)
make docker-compose-services-up

# 2. Launch the API (in one terminal)
make run-api

# 3. Launch the user interface (in another terminal)
make run-ui
```
