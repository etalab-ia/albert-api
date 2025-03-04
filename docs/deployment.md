# Déploiement

### Variables d'environnements

#### API

| Variable | Requis | Type | Defaut | Description |
| --- | --- | --- | --- | --- |
| APP_NAME | Optionnel | str | "Albert API" | Nom de l'application (défaut : "Albert API"). Ce nom sera utilisé la réponse du endpoint `/v1/models` pour la clef `owned_by` des modèles. |
| APP_CONTACT_URL | Optionnel | str | None | URL pour les informations de contact de l'application |
| APP_CONTACT_EMAIL | Optionnel | str | None | Email de contact pour l'application |
| APP_VERSION | Optionnel | str | "0.0.0" | Version de l'application |
| APP_DESCRIPTION | Optionnel | str | None | Description de l'application |
| CONFIG_FILE | Optionnel | str | "config.yml" | Chemin vers le fichier de configuration |
| MIDDLEWARES | Optionnel | bool | True | Activer ou désactiver les middlewares |
| LOG_LEVEL | Optionnel | str | "INFO" | Niveau de journalisation, affiche les endpoints `/health` et `/metrics` dans le schéma Swagger si `DEBUG` |
| DISABLED_ROUTERS | Optionnel | Liste des routers de l'API désactivés (défaut : []). A entrer sous forme de liste python, exemple `DISABLED_ROUTERS='["embeddings", "audio"]'` |

#### UI

| Variable | Requis | Type | Defaut | Description |
| --- | --- | --- | --- | --- |
| BASE_URL | Requis | str | "http://localhost:8080/v1" | URL de l'API |
| EXCLUDE_MODELS | Optionnel | list[str] | [] | Liste des modèles à exclure de l'UI |
| DOCUMENTS_EMBEDDINGS_MODEL | Requis | str | Modèle de documents embeddings |
| SUMMARIZE_TOC_MODEL | Requis | str | Modèle de résumé de table des matières |
| SUMMARIZE_SUMMARY_MODEL | Requis | str | Modèle de résumé de sommaire |
| DEFAULT_CHAT_MODEL | Optionnel | str | None | Modèle de chat par défaut |

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
| by_user | Optionnel | Définit la limite de fréquence d'accès à l'API par utilisateur. | str |

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
| default_internet | Optionnel | Indique si le modèle sera le modèle utilisé pour la recherche sur internet (défaut : False). | bool | (2) |
| aliases | Optionnel | Alias du modèle. | list[str] |  |
| routing_strategy | Optionnel | Stratégie de routage du modèle (défaut : `suffle`). | str | (3) |
| clients | Requis | Définit les clients tiers nécessaires pour le modèle. | list[dict] | |
| clients.model | Requis | ID du modèle tiers. | str | (4) |
| clients.type | Requis | Type du client tiers. | str | `openai`,`vllm`,`tei`,`albert` (5) |
| clients.owned_by | Optionnel | Propriétaire du modèle (défaut : "Albert API"). | str | |
| clients.args | Requis | Arguments du client tiers. | dict | |
| clients.args.api_url | Requis | URL de l'API du client tiers. | str | (6) |
| clients.args.api_key | Requis | Clé API du client tiers. | str | |
| clients.args.timeout | Optionnel | Timeout (en secoundes) de la requête au client tiers (défaut : 120). | int | |

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
          api_url: https://api.openai.com
          api_key: sk-...sA
          timeout: 60
      - model: meta-llama/Llama-3.1-8B-Instruct
        type: vllm
        args:
          api_url: http://localhost:8000
          api_key: sf...Df
          timeout: 60

  - id: embeddings
    type: text-embeddings-inference
    default_internet: True
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

**(3) Stratégie de routage**

Voir [routing - Les stratégies-de-routage](routing.md#stratégies-de-routage).

**(4) Model**

Voir [routing - Exemple de configuration](routing.md#exemple-de-configuration).

**(5) Types de client de modèle**

| Type | Documentation |
| --- | --- |
| `openai` | [OpenAI](https://openai.com/) |
| `vllm` | [vLLM](https://github.com/vllm-project/vllm) |
| `tei` | [HuggingFace Text Embeddings Inference](https://github.com/huggingface/text-embeddings-inference) |

Pour plus d'informations, voir [models](./models.md).

**(6) Format de `api_url` par type de client**

Uniquement la racine de l'URL doit être renseignée, ne pas inclure `/v1` dans l'URL.

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
