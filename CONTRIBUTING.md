# Contributions

Pour contribuer au projet, merci de suivre les instructions suivantes.

> ⚠️ **Attention** : Vous devez disposer d'une API de modèle de language et d'embeddings pour lancer l'API en local.

# Commit 

Merci de respecter la convention suivante pour vos commits :

```
[doc|feat|fix](*) commit object (in english)

# example
feat(collections): collection name retriever
```

*Le thème est optionnel et doit correspondre à un thématique de la code base (deploy, collections, models, ...).

# Packages

1. Dans un environnement virtuel Python, installez les packages Python présents dans le fichier *[pyproject.toml](./pyproject.toml)*

  ```bash 
  pip install ".[ui,app,dev,test]"
  pre-commit install
  ```

# Lancement des services

Pour plus d'information sur le déploiement des services, veuillez consulter la [documentation dédiée](./docs/deployment.md).

## API (FastAPI)

1. Après avoir créé un fichier *config.yml*, lancez l'API en local

    ```bash
    uvicorn app.main:app --port 8080 --log-level debug --reload
    ```

## User interface (Streamlit)

1. Exportez les variables d'environnement nécessaires

    ```bash
    export BASE_URL=http://localhost:8080/v1
    export DOCUMENTS_EMBEDDINGS_MODEL=
    export SUMMARIZE_TOC_MODEL=
    export SUMMARIZE_SUMMARY_MODEL=

2. Lancez l'API en local

    ```bash
    uvicorn app.main:app --port 8080 --log-level debug --reload
    ``` 

3. Lancez l'UI en local

    ```bash
    python -m streamlit run ui/chat.py --server.port 8501 --browser.gatherUsageStats false --theme.base light
    ```

# Tests

Merci, avant chaque pull request, de vérifier le bon déploiement de votre API en exécutant des tests unitaires.

1. Lancez l'API en local avec la commande suivante:

    ```bash
    uvicorn app.main:app --port 8080 --log-level debug --reload
    ```

2. Exécutez les tests unitaires à la racine du projet
    
    ```bash
    PYTHONPATH=. pytest --config-file=pyproject.toml --base-url http://localhost:8080/v1 --api-key-user API_KEY_USER --api-key-admin API_KEY_ADMIN --log-cli-level=INFO
    ```

# Notebooks

Il est important de tenir à jour les notebooks de docs/tutorials, afin de montrer des rapides exemples d'utilisation de l'API.

Pour lancer les notebooks en local:

```bash
jupyter notebook docs/tutorials/
```

# Linter

Le linter du projet est [Ruff](https://beta.ruff.rs/docs/configuration/). Les règles de formatage spécifiques au projet sont dans le fichier *[pyproject.toml](./pyproject.toml)*.

## Configurer Ruff avec pre-commit

1. Installez les hooks de pre-commit

    ```bash
    pre-commit install
    ```

    Ruff s'exécutera automatiquement à chaque commit.

## Configurer Ruff sur VSCode

1. Installez l'extension *Ruff* (charliermarsh.ruff) dans VSCode
2. Configurez le linter Ruff dans VSCode pour utiliser le fichier *[pyproject.toml](./pyproject.toml)*

    À l'aide de la palette de commandes de VSCode (⇧⌘P), recherchez et sélectionnez *Preferences: Open User Settings (JSON)*.

    Dans le fichier JSON qui s'ouvre, ajoutez à la fin du fichier les lignes suivantes :

    ```json
    "ruff.configuration": "<path to pyproject.toml>",
    "ruff.format.preview": true,
    "ruff.lineLength": 150,
    "ruff.codeAction.fixViolation": {
        "enable": false
    },
    "ruff.nativeServer": "on"
    ```

    ⚠️ **Attention** : Assurez-vous que le fichier *[pyproject.toml](./app/pyproject.toml)* est bien spécifié dans la configuration.

3. **Pour exécuter le linter, utilisez la palette de commandes de VSCode (⇧⌘P) depuis le fichier sur lequel vous voulez l'exécuter, puis recherchez et sélectionnez *Ruff: Format document* et *Ruff: Format imports*.**
