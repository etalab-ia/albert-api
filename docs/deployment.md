# Deployment

### Run services

1. Create a configuration file (see the following [configuration section](./deployment.md#configuration)) `config.yml` on the root of the project. A example configuration file is available [here](../config.example.yml).

2. Deploy the services with the following command:

  ```bash
  docker compose --file compose.prod.yml up --detach
  ```

### First authentication

Connect to the playground UI (http://localhost:8501) with the master username as login (`master`) and the master key (`changeme`) as password (see the following [auth section](#auth) to change the default values).

  ![Security](assets/deployment_001.png)

  Go to the *admin* page and create a role with admin appropriate permissions and a user with that role.

### Environment Variables

| Variable | Required | Type | Default | Description |
| --- | --- | --- | --- | --- |
| CONFIG_FILE | Optional | str | "config.yml" | Path to the configuration file |

### Configuration

The Albert API requires configuring a configuration file (config.yml). This defines third-party clients and configuration parameters.
**The configuration file is a YAML file that can combine the configuration of the playground and the API.**

You can consult the Pydantic schema of the configuration for the API [here](../app/schemas/core/settings.py) and for the playground [here](../ui/settings.py).

#### Secrets

You can pass environment variables in configuration file with pattern `${ENV_VARIABLE_NAME}`. All environment variables will be loaded in the configuration file.

**Example**

```yaml
databases:
  - type: sql
    args:
      url: postgresql://${POSTGRES_USER}:${POSTGRES_PASSWORD}@${POSTGRES_HOST}:${POSTGRES_PORT}/${POSTGRES_DB}
```

#### Sections

The configuration file has the following sections:

| Section | Required | Description |
| --- | --- | --- |
| [general](#general) | Required | General configuration. |
| [auth](#auth) | Optional | Authentication parameters. |
| [playground](#playground) | Optional | Playground parameters. |
| [monitoring](#monitoring) | Optional | Monitoring parameters. |
| [models](#models) | Required | Defines model APIs. |
| [web_search](#web_search) | Optional | Defines the internet search engine API. |
| [databases](#databases) | Required | Defines database APIs. |

#### general

| Argument | Required | Description | Type | Values | Default |
| --- | --- | --- | --- | --- | --- |
| title | Optional | API title. | str | | `"Albert API"` |
| version | Optional | API version. | str | | `"latest"` |
| summary | Optional | API summary. | str | | `"Albert API connect to your models."` |
| description | Optional | API description. | str | | `"[See documentation](https://github.com/etalab-ia/albert-api/blob/main/README.md)"` |
| terms_of_service | Optional | API terms of service. | str | | `None` |
| licence_name | Optional | API licence name. | str | | `"MIT License"` |
| licence_identifier | Optional | API licence identifier. | str | | `"MIT"` |
| licence_url | Optional | API licence URL. | str | | `"https://raw.githubusercontent.com/etalab-ia/albert-api/refs/heads/main/LICENSE"` |
| contact_name | Optional | API contact name. | str | | `None` |
| contact_url | Optional | API contact URL. | str | | `None` |
| contact_email | Optional | API contact email. | str | | `None` |
| docs_url | Optional | API swagger URL. | str | | `"/docs"` |
| redoc_url | Optional | API redoc URL. | str | | `"/redoc"` |x
| openapi_url | Optional | API openapi URL. | str | | `"/openapi.json"` |
| log_level | Required | Logging level. | str | `"DEBUG"`, `"INFO"`, `"WARNING"`, `"ERROR"`, `"CRITICAL"` | `"INFO"` |
| disabled_routers | Required | List of disabled API routers. | List[str] | `["audio", "auth", "chat", "chunks", "collections", "documents", "embeddings", "files", "models", "monitoring", "ocr", "rerank", "search"]` | `[]` |
| tokenizer | Optional | Tokenizer type. | str | (1) | `"tiktoken_o200k_base"` |

**Example**
```yaml
general:
  app_name: "Test"
  app_version: "0.0.1"
  disabled_routers: ["documents", "chunks", "collections", "rerank", "search"]
  disabled_middlewares: False
  log_level: "DEBUG"
```

**(1) Tokenizer Types**

Tokenizer is used to count the number of tokens sent by users to compute token per minute (TPM) and token per day (TPD) limits and costs.

| Type | Documentation |
| --- | --- |
| `tiktoken_cl100k_base` | [tiktoken_cl100k_base](https://github.com/openai/tiktoken) |
| `tiktoken_gpt2` | [tiktoken_gpt2](https://github.com/openai/tiktoken) |
| `tiktoken_o200k_base` | [tiktoken_o200k_base](https://github.com/openai/tiktoken) |
| `tiktoken_o50k_base` | [tiktoken_o50k_base](https://github.com/openai/tiktoken) |
| `tiktoken_p50k_base` | [tiktoken_p50k_base](https://github.com/openai/tiktoken) |
| `tiktoken_p50k_edit` | [tiktoken_p50k_edit](https://github.com/openai/tiktoken) |
| `tiktoken_r50k_base` | [tiktoken_r50k_base](https://github.com/openai/tiktoken) |

#### auth
  
| Argument | Required | Description | Type | Values | Default |
| --- | --- | --- | --- | --- | --- |
| master_username | Optional | Master username for the playground. This user can connect to the playground and create users and roles when the SQL database is empty. | str |  | `"master"` | 
| master_key | Optional | API key and password (on playground) for the master user. This key has all permissions and cannot be modified or deleted. This key is also used to encrypt user tokens.  | str |  | `"changeme"` |
| max_token_expiration_days | Optional | Maximum days a user can keep a token. | int | | `365` |
> **❗️Note**<br>
> If you modify the master key, you'll need to update all user API keys.

**Example**
```yaml
auth:
  master_username: "master"
  master_key: "changeme"
  max_token_expiration_days: 20
```

#### models

| Argument | Required | Description | Type | Values | Default |
| --- | --- | --- | --- | --- | --- |
| id | Required | Model ID displayed by the API. | str | | | 
| type | Required | Model type. | str | (1) | |
| aliases | Optional | Model aliases. | list[str] |  | `[]` | 
| owned_by | Optional | Model owner displayed by the `/v1/models` endpoint. | str | | `"Albert API"` |
| routing_strategy | Optional | Model routing strategy | str | (2) | `"shuffle"` |
| clients | Required | Defines the third-party clients required for the model. | list[dict] | |
| clients.model | Required | Third-party model ID. | str | (3) | |
| clients.type | Required | Third-party client type. | str | (4) | |
| clients.costs | Optional | Third-party client costs. | dict | |
| clients.costs.prompt_tokens | Optional | Cost per prompt token. | float | | `0.0` |
| clients.costs.completion_tokens | Optional | Cost per completion token. | float | | `0.0` |
| clients.args | Required | Third-party client arguments. | dict | |
| clients.args.api_url | Required | Third-party client API URL. | str | (5) | |
| clients.args.api_key | Required | Third-party client API key. | str | |
| clients.args.timeout | Optional | Timeout (in seconds) for the request to the third-party client | int | | `300` |

**Example**

```yaml
models: 
  - id: my-language-model
    type: text-generation
    aliases: ["turbo-alias"]
    routing_strategy: round_robin
    clients:
      - model: gpt-3.5-turbo 
        type: openai
        args:
          api_url: https://api.openai.com
          api_key: sk-...sA
          timeout: 60
      - model: meta-llama/Llama-3.1-8B-Instruct
        type: vllm
        args:
          api_url: http://localhost:8000
          api_key: sf...Df
          timeout: 60

  - id: my-embeddings-model
    type: text-embeddings-inference
    clients:
      - model: text-embedding-ada-003
        type: openai
        costs:
          prompt_tokens: 0.01
        args:
          api_url: https://api.openai.com
          api_key: sk-...sA
          timeout: 60
      - model: bge-m3
        type: tei
        costs:
          prompt_tokens: 0.01
        args:
          api_url: http://localhost:8001
          api_key: sf...Df
          timeout: 60
```

**(1) Model Types**

Model types correspond to the convention proposed by HuggingFace Hub. The configuration file must declare at least one model of type `text-generation` and one model of type `text-embeddings-inference`.

| Type | Equivalent | Example |
| --- | --- | --- |
| `text-generation`| Large language model | [meta-llama/Llama-3.1-8B-Instruct](https://huggingface.co/meta-llama/Llama-3.1-8B-Instruct)
| `text-embeddings-inference`| Embeddings model | [BAAI/bge-m3](https://huggingface.co/BAAI/bge-m3)
| `text-classification`| Reranking model | [BAAI/bge-reranker-v2-m3](https://huggingface.co/BAAI/bge-reranker-v2-m3)
| `automatic-speech-recognition`| Audio transcription | [openai/whisper-large-v3](https://huggingface.co/openai/whisper-large-v3)

**(2) Routing Strategy**

See [routing - Routing Strategies](routing.md#stratégies-de-routage).

**(3) Model**

See [routing - Configuration Example](routing.md#exemple-de-configuration).

**(4) Model Client Types**

| Type | Documentation |
| --- | --- |
| `openai` | [OpenAI](https://openai.com/) |
| `vllm` | [vLLM](https://github.com/vllm-project/vllm) |
| `tei` | [HuggingFace Text Embeddings Inference](https://github.com/huggingface/text-embeddings-inference) |
| `albert` | [Albert API](https://github.com/etalab/albert-api) |

For more information, see [models](./models.md).

**(5) `api_url` format by client type**

Only the root of the URL should be provided, do not include `/v1` in the URL.

#### databases

| Argument | Required | Description | Type | Values | Default |
| --- | --- | --- | --- | --- | --- |
| type | Required | Defines the database type. | str | `redis`, `qdrant`, `sql` (1) | |
| context | Optional | Defines the database context. | str | `api`, `playground` (2) | Depends of the service launched. | 
| model | Optional | A text-embeddings-inference model ID if required for Qdrant. | str | (3) | `None` | 
| args | Required | Database arguments. | dict | (4) | |

**Requirements:**
- You must define at least two different `sql` databases, one for the API and one for the playgroud. By default, the [docker compose file](../compose.yml), that defined databases, provides an [entrypoint for Postgres](../scripts/postgres_entrypoint.sh) to create automatically two databases (*api* and *playground*, setup by environment variable `CREATE_DB` in Postgres docker container).
- To activate RAG features, you must define a Qdrant database.
- To activate web search features, you must define a Qdrant database.

**Example**

```yaml
databases:
  - type: qdrant
    model: my-embeddings-model
    args:
      url: http://localhost:6333
      api_key: yU..SB
      prefer_grpc: True
      grpc_port: 6334
      timeout: 10

  - type: redis
    args:
      host: localhost
      port: 6379
      password: changeme
  
  - type: sql # API database (async)
    context: api
    args:
      url: postgresql+asyncpg://postgres:changeme@localhost:5432/api
      echo: False
      pool_size: 5
      max_overflow: 10
      pool_pre_ping: True
      connect_args: {"server_settings": {"statement_timeout": "120s"}}

  - type: sql # Playground database (sync)
    context: playground
    args:
      url: postgresql://postgres:changeme@localhost:5432/playground
      echo: False
      pool_size: 5
      max_overflow: 10
      pool_pre_ping: True
```   

**(1) Database Types**

| Type | Required | Usage | Documentation |
| --- | --- | --- | --- |
| `redis` | Required | Rate limiting | [Redis](https://redis.io/) |
| `qdrant` | Required | Vector store | [Qdrant](https://qdrant.tech/) |
| `sql` | Required | Ressources and authentication (different databases for API and playground) | [SQLAlchemy](https://www.sqlalchemy.org/) |

**(2) Database Context**

Because the configuration file must be combined with the playground configuration, the `context` argument defines the database context (`api` or `playground`). The `api` context is used to store the API data and the `playground` context to store the playground data. 

If you launch only the API, without the playgroud, you can only define one `sql` database without the `context` keyword.

**(3) Qdrant Database Model**

Qdrant is a vector database that allows you to store and retrieve vectors. The `model` argument is the ID of a text-embeddings-inference model defined in the `models` section. This model is used to embed the queries when performing a similarity search.

> **❗️Note**<br>
> If you change the model of a Qdrant database, you need to re-embed the database.

**(4) Database Client Arguments**

The database arguments are those accepted by the respective Python clients of these databases:
- [Redis client](https://github.com/redis/redis-py)
- [Qdrant client](https://github.com/qdrant/qdrant-client)
- [SQLAlchemy client](https://www.sqlalchemy.org/)

#### playground

The `playground` section allows you to configure the playground.

| Argument | Required | Description | Type | Values | Default |
| --- | --- | --- | --- | --- | --- |
| api_url | Required | Playground API URL. | str | | `"http://localhost:8000"` |
| home_url | Required | Playground home URL to redirect to when user click on the logo. | str | | `"http://localhost:8501"` |
| page_icon | Required | Playground page icon URL. | str | | `"https://github.com/etalab-ia/albert-api/blob/main/docs/assets/logo.png?raw=true"` |
| logo | Required | Playground logo URL. | str | | `"https://github.com/etalab-ia/albert-api/blob/main/docs/assets/logo.png?raw=true"` |
| menu_items | Optional | Configure the menu that appears on the top-right side of this app. See [Streamlit st.set_page_config documentation](https://docs.streamlit.io/develop/api-reference/configuration/st.set_page_config) for more information. | list[dict] | | `[]` |
| menu_items.get_help | Optional | The URL this menu item should point to. If None, hides this menu item. The URL may also refer to an email address e.g. `mailto:john@example.com.` | str | | `None` |
| menu_items.report_a_bug | Optional | The URL this menu item should point to. If None, hides this menu item. The URL may also refer to an email address e.g. `mailto:john@example.com.` | str | | `None` |
| menu_items.about | Optional | A markdown string to show in the About dialog. If None, only shows Streamlit's default About text. | str | | `None` |
| cache_ttl | Required | Cache TTL (in seconds). | int | | `1800` |

**Example**

```yaml
playground:
  api_url: http://localhost:8081
  home_url: http://localhost:8501/playground
  page_icon: https://github.com/etalab-ia/albert-api/blob/main/docs/assets/logo.png?raw=true
  logo: https://github.com/etalab-ia/albert-api/blob/main/docs/assets/logo.png?raw=true
  menu_items:
    get_help: mailto:contact@example.com
    report_a_bug: https://github.com/etalab-ia/albert-api/issues
    about: "This is a playground for the Albert API."
  cache_ttl: 1800
```

#### monitoring

| Argument | Required | Description | Type | Values | Default |
| --- | --- | --- | --- | --- | --- |
| router | Optional | Log usage of the specified routers. | List[str] |  `["all", "audio", "auth", "chat", "chunks", "collections", "documents", "embeddings", "files", "models", "monitoring", "ocr", "rerank", "search"]` | `[]` (1) |
| tokenizer | Optional | Tokenizer type. | str | (2) | `"tiktoken_o200k_base"` |

**(1) Router Types**

If `router` is set to `all`, all routers will be logged. This option is exclusive with the `router` argument. `monitoring` and `files` routers can be specified but will be ignored (not implemented yet).

**(2) Tokenizer Types**


#### web_search

The Albert API allows searching the internet to enrich API responses. For this, it is necessary to configure a search engine API client in the `web_search` section.

Prerequisites:
- Qdrant database
- SQL database
- A text-generation or image-text-to-text model
- A text-embeddings-inference model

| Argument | Required | Description | Type | Values | Default |
| --- | --- | --- | --- | --- | --- |
| query_model | Required | Model to use to generate the web query, only text-generation and image-text-to-text models are supported. | str | | |
| limited_domains | Optional | List of domains to limit the web search to. | list[str] | | `[]` |
| user_agent | Optional | User agent to use for the scrapping requests. | str | | `None` |
| client | Required | Web search client to use. | dict | (1) | |
| client.type | Optional | Web search client type. | str | (2) | `duckduckgo` |
| client.args | Optional | Web search client arguments (depends on the web search client type). | dict | (3) | |

**Example**

```yaml
web_search:
  query_model: my-language-model
  limited_domains:
    - service-public.fr
    - gouv.fr
  user_agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3
  client:
    type: brave
    args:
      api_key: xP...Df
      timeout: 30
```

**(1) Web Search Engine Types**

| Type | Documentation |
| --- | --- |
| `brave` | [Brave](https://brave.com/) |
| `duckduckgo` | [DuckDuckGo](https://duckduckgo.com/) |

**(2) Web Search Model**

The user prompt will be converted into a search query using a text-generation model. The `model` argument is the ID of a text-generation model defined in the `models` section.
