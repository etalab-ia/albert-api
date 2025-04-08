# Deployment

### Environment Variables

#### API


| Variable | Required | Type | Default | Description |
| --- | --- | --- | --- | --- |
| APP_NAME | Optional | str | "Albert API" | Application name (default: "Albert API"). This name will be used in the response of the `/v1/models` endpoint for the `owned_by` key of the models. |
| APP_CONTACT_URL | Optional | str | None | URL for application contact information |
| APP_CONTACT_EMAIL | Optional | str | None | Contact email for the application |
| APP_VERSION | Optional | str | "0.0.0" | Application version |
| APP_DESCRIPTION | Optional | str | None | Application description |
| CONFIG_FILE | Optional | str | "config.yml" | Path to the configuration file |
| MIDDLEWARES | Optional | bool | True | Enable or disable middlewares |
| LOG_LEVEL | Optional | str | "INFO" | Logging level, displays `/health` and `/metrics` endpoints in the Swagger schema if set to `DEBUG` |
| DISABLED_ROUTERS | Optional | List of disabled API routers (default: []). Enter as a Python list, example `DISABLED_ROUTERS='["embeddings", "audio"]'` |


#### UI

| Variable | Requis | Description |
| --- | --- | --- |
| BASE_URL | Requis | URL de l'API (défaut : "http://localhost:8080/v1") |
| EXCLUDE_MODELS | Optionnel | Liste des modèles à exclure de l'UI (défaut : None) |
| DOCUMENTS_EMBEDDINGS_MODEL | Requis | Modèle de documents embeddings |
| SUMMARIZE_TOC_MODEL | Requis | Modèle de résumé de table des matières |
| SUMMARIZE_SUMMARY_MODEL | Requis | Modèle de résumé de sommaire |
| DEFAULT_CHAT_MODEL | Optionnel | Modèle de chat par défaut (défaut : None) |

### Configuration

To function, the Albert API requires configuring the configuration file (config.yml). This defines third-party clients and configuration parameters.

You can consult the Pydantic schema of the configuration [here](../app/schemas/settings.py).

#### Sections

The configuration file has the following sections:

| Section | Required | Description |
| --- | --- | --- |
| auth | Optional | Authentication parameters. |
| playground | Optional | Playground parameters. |
| models | Required | Defines model APIs. |
| web_search | Optional | Defines the internet search engine API. |
| databases | Required | Defines database APIs. |

#### auth
  
| Argument | Required | Description | Type | Values | Default |
| --- | --- | --- | --- | --- | --- |
| master_username | Optional | Master username for the playground. This user can connect to the playground and create users and roles when the SQL database is empty. | str |  | `"master"` | 
| master_key | Optional | API key and password (on playground) for the master user. This key has all permissions and cannot be modified or deleted. This key is also used to encrypt user tokens.  | str |  | `"changeme"` |

> [!NOTE] If you modify the master key, you'll need to update all user API keys.

**Example**
```yaml
auth:
  master_username: "master"
  master_key: "changeme"
```

#### models

| Argument | Required | Description | Type | Values | Default |
| --- | --- | --- | --- | --- | --- |
| id | Required | Model ID displayed by the API. | str | | | 
| type | Required | Model type. | str | (1) |
| aliases | Optional | Model aliases. | list[str] |  | `[]` | 
| owned_by | Optional | Model owner displayed by the `/v1/models` endpoint. | str | | `"Albert API"` |
| routing_strategy | Optional | Model routing strategy | str | (2) | `"shuffle"` |
| clients | Required | Defines the third-party clients required for the model. | list[dict] | |
| clients.model | Required | Third-party model ID. | str | (3) |
| clients.type | Required | Third-party client type. | str | (4) |
| clients.args | Required | Third-party client arguments. | dict | |
| clients.args.api_url | Required | Third-party client API URL. | str | (5) |
| clients.args.api_key | Required | Third-party client API key. | str | |
| clients.args.timeout | Optional | Timeout (in seconds) for the request to the third-party client | int | | `300` |

**Example**

```yaml
models: 
  - id: my-language-model
    type: text-generation
    aliases: ["turbo-alias"]
    default_internet: True
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
        args:
          api_url: https://api.openai.com
          api_key: sk-...sA
          timeout: 60
      - model: bge-m3
        type: tei
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

| Argument | Required | Description | Type | Values |
| --- | --- | --- | --- | --- |
| type | Required | Defines the database type. | str | `redis`, `qdrant`, `sql` (1) |
| model | Optional | A text-embeddings-inference model ID if required for Qdrant. | str | (2) |
| args | Required | Database arguments. | dict | (3) |

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
  
  - type: sql
    args:
      url: postgresql://postgres:changeme@localhost:5432/api
      echo: False
      pool_size: 5
      max_overflow: 10
      pool_pre_ping: True
      connect_args: {"server_settings": {"statement_timeout": "60"}}
```   

**(1) Database Types**

| Type | Required | Usage | Documentation |
| --- | --- | --- | --- |
| `redis` | Required | Cache and rate limiting | [Redis](https://redis.io/) |
| `qdrant` | Required | Vector store | [Qdrant](https://qdrant.tech/) |
| `sql` | Required | Relational database | [SQLAlchemy](https://www.sqlalchemy.org/) |

**(2) Qdrant Database Model**

Qdrant is a vector database that allows you to store and retrieve vectors. The `model` argument is the ID of a text-embeddings-inference model defined in the `models` section. This model is used to embed the queries when performing a similarity search.

> [!NOTE] If you change the model of a Qdrant database, you need to re-embed the database.

**(3) Database Client Arguments**

The database arguments are those accepted by the respective Python clients of these databases:
- [Redis client](https://github.com/redis/redis-py)
- [Qdrant client](https://github.com/qdrant/qdrant-client)
- [SQLAlchemy client](https://www.sqlalchemy.org/)

#### playground

The `playground` section allows you to configure the playground.

| Argument | Required | Description | Type | Values | Default |
| --- | --- | --- | --- | --- | --- |
| api_url | Required | Playground API URL. | str | |
| max_api_key_expiration_days | Required | Maximum days a user can keep an API key. | int | | `365` |
| cache_ttl | Required | Cache TTL (in seconds). | int | | `1800` |
| database_url | Required | Database URL. | str | | |

**Example**

```yaml
playground:
  api_url: http://localhost:8081
  max_api_key_expiration_days: 365
  cache_ttl: 1800
  database_url: postgresql://postgres:changeme@localhost:5432/ui
```

#### web_search

The Albert API allows searching the internet to enrich API responses. For this, it is necessary to configure a search engine API client in the `web_search` section.

Prerequisites:
- Qdrant database
- SQL database
- A text-generation model
- A text-embeddings-inference model

| Argument | Required | Description | Type | Values | Default |
| --- | --- | --- | --- | --- | --- |
| type | Required | Internet search engine type. | str | (1) | `duckduckgo` | 
| model | Required | A text-generation model ID if required for web search. | str | (2) |
| args | Required | Search engine client arguments. | dict | |

**Example**

```yaml
internet:
  - type: brave
    model: my-language-model
    args:
      api_key: xP...Df
```

**(1) Web Search Engine Types**

| Type | Documentation |
| --- | --- |
| `brave` | [Brave](https://brave.com/) |
| `duckduckgo` | [DuckDuckGo](https://duckduckgo.com/) |

**(2) Web Search Model**

The user prompt will be converted into a search query using a text-generation model. The `model` argument is the ID of a text-generation model defined in the `models` section.
