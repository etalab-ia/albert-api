# Integration tests

> [!WARNING]
> **For internal team use only.**

The configuration file is in the `app/tests/integ/config.test.yml` file.

## Run integration tests

### Prerequisites

- Docker
- Docker Compose
- Virtual environment with packages installed (see [CONTRIBUTING.md](../CONTRIBUTING.md)) (optional)

### Start services and run tests

To start services and run tests, you can use the following command:

```bash
make test-integ 
```

### Start services for integration tests

To start services for integration tests without running tests, you can use the following command:

```bash
make test-integ [action=up|down|run|all] [execute=local|docker]
```

> [!NOTE]
> The `action` parameter is optional and defaults to `all`. This parameter is used to specify the action to perform:
> - `up`: Setup environment without running tests
> - `down`: Shutdown services and clean up environment
> - `run`: Run tests without setup environment
> - `all`: Setup environment and run tests

> The `execute` parameter is optional and defaults to `local`. This parameter is used to specify the execution environment of tests:
> - `local`: Run tests in local environment
> - `docker`: Run tests in docker environment (like in CI/CD)

> [!NOTE]
> To run the integration tests locally, you need to set the following environment variables in the `.github/.env.ci` file:
>
> - `POSTGRES_HOST` must be set to `localhost`
> - `REDIS_HOST` must be set to `localhost`
> - `ELASTICSEARCH_HOST` must be set to `localhost`
> - `SECRETIVESHELL_HOST` must be set to `localhost`
> - `BRAVE_API_KEY` must be set to your Brave API key
> - `ALBERT_API_KEY` must be set to your Albert API key

### Example

* Run tests in local environment:

    ```bash
    make test-integ action=run execute=local
    ```

* Setup environment before running tests:

    ```bash
    make test-integ action=up execute=local
    ```

    Then run tests:

    ```bash
    make test-integ action=run execute=local
    ```

* Shutdown services and clean up environment:

    ```bash
    make test-integ action=down execute=local
    ```
