## Déployer l'API Albert

### Quickstart

1. Installez [libmagic](https://man7.org/linux/man-pages/man3/libmagic.3.html)

2. Installez les packages Python dans un environnement virtuel dédié

  ```bash 
  pip install ".[app]"
  ```

3. Créez un fichier *config.yml* à la racine du repository sur la base du fichier d'exemple *[config.example.yml](./config.example.yml)*

  Si vous souhaitez configurer les accès aux modèles et aux bases de données, consultez la [Configuration](#configuration).

  Pour lancer l'API : 
  ```bash
  uvicorn app.main:app --reload --port 8080 --log-level debug
  ```

### Configuration

Toute la configuration de l'API Albert se fait dans fichier de configuration qui doit respecter les  spécifications suivantes (voir *[config.example.yml](./config.example.yml)* pour un exemple) :

```yaml
auth: [optional]
  type: [optional]
  args: [optional] 
    [arg_name]: [value]
    ...
  
models:
    - url: [required]
      key: [optional]
      search_internet: [optional]
    ...

databases:
  cache: [required]
    type: [required] # see following Database section for the list of supported db type
    args: [required] 
      [arg_name]: [value]
      ...
    
  vectors: [required]
    type: [required] # see following Database section for the list of supported db type
    args: [required] 
      [arg_name]: [value]
      ...
```

**Par défaut, l'API va chercher un fichier nommé *config.yml* la racine du dépot.** Néanmoins, vous pouvez spécifier un autre fichier de config comme ceci :

```bash
CONFIG_FILE=<path_to_the_file> uvicorn main:app --reload --port 8080 --log-level debug
``` 

La configuration permet de spéficier le token d'accès à l'API, les API de modèles auquel à accès l'API d'Albert ainsi que les bases de données nécessaires à sont fonctionnement. 

#### Auth

Les IAM supportés, de nouveaux seront disponibles prochainement :

* [Grist](https://www.getgrist.com/)

#### Databases

Voici les types de base de données supportées, à configurer dans le fichier de configuration (*[config.example.yml](./config.example.yml)*) : 

| Database | Type |
| --- | --- |
| vectors | [qdrant](https://qdrant.tech/) | 
| cache | [redis](https://redis.io/) |

## Déploiement de l'interface Streamlit

1. Installez les packages Python dans un environnement virtuel

  ```bash 
  pip install ".[ui]"
  ```

2. Exécutez l'application Streamlit

  ```bash
  streamlit run ui/chat.py --server.port 8501 --browser.gatherUsageStats false --theme.base light
  ```
