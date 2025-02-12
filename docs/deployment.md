# Déploiement

### Variables d'environnements

| Variable | Description |
| --- | --- |
| APP_NAME | Nom de l'application (par défaut : "Albert API"). Ce nom sera utilisé la réponse du endpoint `/v1/models` pour la clef `owned_by` des modèles. |
| APP_CONTACT_URL | URL pour les informations de contact de l'application (par défaut : None) |
| APP_CONTACT_EMAIL | Email de contact pour l'application (par défaut : None) |
| APP_VERSION | Version de l'application (par défaut : "0.0.0") |
| APP_DESCRIPTION | Description de l'application (par défaut : None) |
| CONFIG_FILE | Chemin vers le fichier de configuration (par défaut : "config.yml") |
| ENABLE_METRICS | Active ou désactive les métriques Prometheus (par défaut : True) |
| LOG_LEVEL | Niveau de journalisation (par défaut : INFO) |

### Configuration

Pour fonctionner, l'API Albert nécessite configurer le fichier de configuration (config.yml). Celui-ci définit les clients tiers et des paramètres de configuration.

Vous pouvez consulter le schéma Pydantic de la configuration [ici](../app/schemas/settings.py).

#### Sections

Les sections du fichier de configuration sont les suivantes :

| Section | Requis | Description |
| --- | --- | --- |
| rate_limit | Optionnel | Définit les limites de fréquence d'accès à l'API. |
| models | Requis | Définit les modèles. |
| internet | Optionel | Définit l'API de moteur de recherche internet. |
| databases | Requis | Définit les bases de données. |

#### rate_limit

| Argument | Requis | Description | Type | Valeurs |
| --- | --- | --- | --- | --- |
| by_ip | Optionnel | Définit la limite de fréquence d'accès à l'API par adresse IP. | str |  | 
| by_user | Optionnel | Définit la limite de fréquence d'accès à l'API par utilisateur. | str | |

**Exemple**
```yaml
rate_limit:
  by_ip: "100/minute"
  by_user: "1000/minute"
```

#### models

| Argument | Requis | Description | Type | Valeurs |
| --- | --- | --- | --- | --- |
| id | Requis | ID du modèle affiché par l'API. | str | | 
| type | Requis | Type de modèle. | str | `text-generation`,`text-embeddings-inference`,`automatic-speech-recognition`,`text-classification` (1) |
| default_internet | Optionnel | Indique si le modèle sera le modèle utilisé pour la recherche sur internet (default : False). | bool | (2) |
| aliases | Optionnel | Alias du modèle. | list[str] |  |
| routing_strategy | Optionnel | Stratégie de routage du modèle (default : `suffle`). | str | (3) |
| clients | Requis | Définit les clients tiers nécessaires pour le modèle. | list[dict] | |
| clients.model | Requis | ID du modèle tiers. | str | (4) |
| clients.type | Requis | Type du client tiers. | str | `openai`,`vllm`,`tei` (5) |
| clients.args | Requis | Arguments du client tiers. | dict | (6) |
| clients.args.base_url | Requis | URL de l'API du client tiers. | str | (7) |
| clients.args.api_key | Requis | Clé API du client tiers. | str | |
| clients.args.timeout | Optionnel | Timeout (en secoundes) de la requête au client tiers (default : 120). | int | |

**Exemple**

```yaml
models:
  - id: turbo
    type: text-generation
    aliases: ["turbo-alias"]
    default_internet: True
    routing_strategy: round_robin
    clients:
      - model: gpt-3.5-turbo 
        type: openai
        args:
          base_url: https://api.openai.com/v1
          api_key: sk-...sA
          timeout: 60
      - model: meta-llama/Llama-3.1-8B-Instruct
        type: vllm
        args:
          base_url: http://.../v1
          api_key: sf...Df
          timeout: 60

  - id: embeddings
    type: text-embeddings-inference
    default_internet: True
    clients:
      - model: text-embedding-ada-003
        type: openai
        args:
          base_url: https://api.openai.com/v1
          api_key: sk-...sA
          timeout: 60
```

**(1) Type de modèle**

Les types de modèles correspondent à la convention proposé par HuggingFace Hub. Le fichier de configuration doit obligatoirement déclaré a minima un modèle de type `text-generation` et un modèle de type `text-embeddings-inference`.

| Type | Equivalent |Exemple|
| --- | --- | --- |
| `text-generation`| Large language model | [meta-llama/Llama-3.1-8B-Instruct](https://huggingface.co/meta-llama/Llama-3.1-8B-Instruct)
| `text-embeddings-inference`| Embeddings model | [BAAI/bge-m3](https://huggingface.co/BAAI/bge-m3)
| `text-classification`| Reranking model | [BAAI/bge-reranker-v2-m3](https://huggingface.co/BAAI/bge-reranker-v2-m3)
| `automatic-speech-recognition`| Audio transcription | [openai/whisper-large-v3](https://huggingface.co/openai/whisper-large-v3)

**(2) Modèles par défaut pour la recherche sur internet**

Voir section [internet](#internet).

**(3) Argument acceptées par le client de modèle**

En plus de `base_url`, `api_key`, `timeout`, les clients de modèle acceptent tous les arguments du client python OpenAI ([voir les arguments](https://github.com/openai/openai-python/blob/7193688e364bd726594fe369032e813ced1bdfe2/src/openai/_client.py#L74)).

**(4) Model**

Voir [routing - Exemple de configuration](routing.md#exemple-de-configuration).

**(5) Stratégie de routage**

Voir [routing - Les stratégies-de-routage](routing.md#stratégies-de-routage).

**(6) Types de client de modèle**

| Type | Documentation |
| --- | --- |
| `openai` | [OpenAI](https://openai.com/) |
| `vllm` | [vLLM](https://github.com/vllm-project/vllm) |
| `tei` | [HuggingFace Text Embeddings Inference](https://github.com/huggingface/text-embeddings-inference) |

Pour plus d'informations, voir [models](./models.md).

**(7) Format de `base_url` par type de client**

| Client | Format |
| --- | --- |
| OpenAI | `http(s)://.../v1` |
| vLLM | `http(s)://.../v1` |
| TEI | `http(s)://...` |

#### databases

| Argument | Requis | Description | Type | Valeurs |
| --- | --- | --- | --- | --- |
| type | Requis | Définit le type de base de données. | str | `redis`, `qdrant`, `grist` (1) |
| args | Requis | Arguments de la base de données. | dict | (2) |

**Exemple**

```yaml
databases:
  - type: qdrant
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
  
  - type: grist
    args:
      api_key: 12..9c
      server: https://grist.numerique.gouv.fr
      doc_id: 4fBA12fFpHuxn38G6sLPMr
      table_id: DEV
```   

**(1) Les types de bases de données**

| Type | Requis | Utilisation | Documentation |
| --- | --- | --- | --- |
| `redis` | Requis | Cache et rate limiting | [Redis](https://redis.io/) |
| `qdrant` | Requis | Vector store | [Qdrant](https://qdrant.tech/) |
| `grist` | Optionnel | Auth | [Grist](https://www.getgrist.com/) |

Si grist n'est pas configuré, l'API Albert est ouverte sans authentification.

**(2) Les arguments des clients de bases de données**

Les arguments des bases de données sont tous ceux acceptés les clients python respectifs de ces bases de données :
- [client Redis](https://github.com/redis/redis-py)
- [client Qdrant](https://github.com/qdrant/qdrant-client)
- [client Grist](https://github.com/gristlabs/py_grist_api)

#### internet

L'API Albert permet de rechercher sur internet pour enrichir les réponses de l'API. Pour cela, il est nécessaire de configurer un client d'une API de moteur de recherche internet. De plus, afin de pouvoir rechercher sur internet, il est nécessaire de configurer au moins un modèle de type `text-generation` et un modèle de type `text-embeddings-inference` avec le paramètre `default_internet` à `True`.

| Argument | Requis | Description | Type | Valeurs |
| --- | --- | --- | --- | --- |
| type | Requis | Type de moteur de recherche internet. | str | `brave`, `duckduckgo` |
| args | Requis | Arguments du client du moteur de recherche internet. | dict | |

**(1) Types de moteurs de recherche internet**

| Type | Documentation |
| --- | --- |
| `brave` | [Brave](https://brave.com/) |
| `duckduckgo` | [DuckDuckGo](https://duckduckgo.com/) |


**Exemple**

```yaml
internet:
  - type: brave
    args:
      api_key: xP...Df
```
