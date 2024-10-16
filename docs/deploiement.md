# Déployer l'API Albert

## Quickstart

1. Créez un fichier *config.yml* à la racine du dépot sur la base du fichier d'exemple *[config.example.yml](./config.example.yml)* Voir la section [Configuration](#configuration) pour plus d'informations.

2. Déployez l'API avec Docker à l'aide du fichier [compose.yml](../compose.yml) à la racine du dépot.

  ```bash
  docker compose up -d
  ```

## Configuration

### Variables d'environnements

| Variable | Description |
| --- | --- |
| APP_CONTACT_URL | URL for app contact information (default: None) |
| APP_CONTACT_EMAIL | Email for app contact (default: None) |
| APP_VERSION | Version of the application (default: "0.0.0") |
| APP_DESCRIPTION | Description of the application (default: None) |
| DEFAULT_RATE_LIMIT | Default rate limit for API requests (default: "100/minute") |
| CORE_RATE_LIMIT | Rate limit for users API (default: "10/minute") |
| CONFIG_FILE | Path to the configuration file (default: "config.yml") |
| LOG_LEVEL | Logging level (default: DEBUG) |

### Clients tiers

Pour fonctionner, l'API Albert nécessite des clients tiers :

* [Optionnel] Auth : [Grist](https://www.getgrist.com/)*
* Cache : [Redis](https://redis.io/)
* Vectors : [Qdrant](https://qdrant.tech/)

\* *Pour plus d'information sur l'authentification Grist, voir la [documentation](./security.md).*

Ces clients sont déclarés dans un fichier de configuration qui doit respecter les  spécifications suivantes (voir *[config.example.yml](./config.example.yml)* pour un exemple) :

```yaml
auth: [optional]
  type: grist
  args: [optional] 
    [arg_name]: [value]
    ...
  
models:
    - url: [required]
      key: [optional]
      search_internet: [optional]
      type: [required] # at least one of embedding model (text-embeddings-inference)

    - url: [required] 
      key: [optional]
      search_internet: [optional]
      type: [required] # at least one of language model (text-generation)
    ...

databases:
  cache: [required]
    type: redis
    args: [required] 
      [arg_name]: [value]
      ...
    
  vectors: [required]
    type: qdrant
    args: [required] 
      [arg_name]: [value]
      ...
```

## Déploiement de l'interface Streamlit

1. Installez les packages Python dans un environnement virtuel

  ```bash 
  pip install ".[ui]"
  ```

2. Exécutez l'application Streamlit

  ```bash
  streamlit run ui/chat.py --server.port 8501 --browser.gatherUsageStats false --theme.base light
  ```
