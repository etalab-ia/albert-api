# Contributing

## Contributing environment

To contribute to the project, please follow the instructions below to setup your development environment and launch the services locally.

### Prerequisites

- Python 3.12+
- Docker and Docker Compose

### Step 1: development environment

#### Configuration

It is recommended to use a Python [virtualenv](https://docs.python.org/3/library/venv.html).

1. Create a *config.yml* file based on the example configuration file *[config.example.yml](./config.example.yml)*. 

  ```bash
  cp config.example.yml config.yml
  ```

2. Create a *env* file based on the example environment file *[env.example](./env.example)*

  ```bash
  cp env.example .env
  ```

3. Replace host names variables by `localhost` like this:

  ```bash
  # example
  POSTGRES_HOST=localhost # instead of POSTGRES_HOST=postgres
  ```

3. Export the environment variables:

  ```bash
  export $(grep -v '^#' .env | xargs)
  ```

4. Check the [configuration documentation](./docs/configuration.md) to configure your configuration file.

#### Packages installation

1. Create a Python virtual environment (recommended)

2. Install the dependencies with the following command:

  ```bash
  pip install ".[app,ui,dev,test]"
  ```

#### Linter installation

The project linter is [Ruff](https://beta.ruff.rs/docs/configuration/). The specific project formatting rules are in the *[pyproject.toml](./pyproject.toml)* file.

Please install the pre-commit hooks:

  ```bash
  pre-commit install
  ```

Ruff will run automatically at each commit.

### Step 2: launch services

Start services locally with the following command:

```bash
make dev
```

> [!NOTE]
> This command will start the API and the playground services and support the following options:
> ```bash
> make dev [service=api|playground|both] [env=.env] [compose=compose.yml]
> ```
> For more information, run `make help`.

## Linter

The project linter is [Ruff](https://beta.ruff.rs/docs/configuration/). The specific project formatting rules are in the *[pyproject.toml](./pyproject.toml)* file. See [Linter installation section](#linter-installation) to install the linter and run it at each commit.

To run the linter manually:

```bash
make lint
```

## Commit

Please respect the following convention for your commits:

```
[doc|feat|fix](theme) commit object (in english)

# example
feat(collections): collection name retriever
```

## Tests

To run the tests:

```bash
make test
```

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
