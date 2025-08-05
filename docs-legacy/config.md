# Configuration

OpenGateLLM requires a configuration file which defines models, dependencies and settings parameters.

By default, the configuration file must be `./config.yml` file.

You can change the configuration file by setting the `CONFIG_FILE` environment variable.

The configuration file has 3 sections:
- `models`: models configuration.
- `dependencies`: dependencies configuration.
- `settings`: settings configuration.

## Secrets

You can pass environment variables in configuration file with pattern `${ENV_VARIABLE_NAME}`. All environment variables will be loaded in the configuration file.

**Example**

```yaml
models:
  - name: my-language-model
    providers:
      - name: openai
        model: gpt-4o-mini
        url: https://api.openai.com
        api_key: ${OPENAI_API_KEY}
        timeout: 60


```

## Models

The `models` section is used to configure the models used by the API.

## Dependencies
