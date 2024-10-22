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
| APP_CONTACT_URL | URL pour les informations de contact de l'application (par défaut : None) |
| APP_CONTACT_EMAIL | Email de contact pour l'application (par défaut : None) |
| APP_VERSION | Version de l'application (par défaut : "0.0.0") |
| APP_DESCRIPTION | Description de l'application (par défaut : None) |
| GLOBAL_RATE_LIMIT | Limite de taux global pour les requêtes API par adresse IP (par défaut : "100/minute") |
| DEFAULT_RATE_LIMIT | Limite de taux par défaut pour les requêtes API par utilisateur (par défaut : "10/minute") |
| CONFIG_FILE | Chemin vers le fichier de configuration (par défaut : "config.yml") |
| LOG_LEVEL | Niveau de journalisation (par défaut : DEBUG) |
| DEFAULT_INTERNET_LANGUAGE_MODEL_URL | URL d'un modèle de langage pour RAG sur la recherche internet (par défaut : premier modèle de langage disponible) |
| DEFAULT_INTERNET_EMBEDDINGS_MODEL_URL | URL d'un modèle d'embeddings pour RAG sur la recherche internet (par défaut : premier modèle d'embeddings disponible) |

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
      type: [required] # at least one of embedding model (text-embeddings-inference)

    - url: [required] 
      key: [optional]
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
