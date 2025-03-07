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

## Base de données (Alembic)

## API (FastAPI)

1. Créez les tables de la base de données

    L'API nécessite une base de données SQL. Vous devez préalablement exécuter les migrations pour créer les tables avec la commande suivante :

    ```bash
    alembic upgrade head
    ```

2. Après avoir créé un fichier *config.yml*, lancez l'API en local

    ```bash
    uvicorn app.main:app --port 8080 --log-level debug --reload
    ```

## User interface (Streamlit)

1. Exportez les variables d'environnement nécessaires

    ```bash
    export BASE_URL=http://localhost:8080/v1
    export DOCUMENTS_EMBEDDINGS_MODEL=
    ```

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

Pour exécuter les tests unitaires à la racine du projet, exécutez la commande suivante :
    
```bash
CONFIG_FILE=<path to config file> PYTHONPATH=. pytest --config-file=pyproject.toml --api-key-user <api key user> --api-key-admin <api key admin>
```

Pour n'exécuter qu'une partie des tests, par exemple les test *audio*, exécutez la commande suivante :

```bash
CONFIG_FILE=<path to config file> PYTHONPATH=. pytest app/tests/test_audio.py --config-file=pyproject.toml --api-key-user <api key user> --api-key-admin <api key admin>
```

Pour mettre à jour les snapshots, exécutez la commande suivante :

```bash
CONFIG_FILE=<path to config file> PYTHONPATH=. pytest --config-file=pyproject.toml --api-key-user <api key user> --api-key-admin <api key admin> --snapshot-update
```

## Configurer les tests dans VSCode

Pour utiliser le module testing de VSCode, veuillez la configuration suivante dans votre fichier *.vscode/settings.json* :

```json
{
    "python.terminal.activateEnvironment": false,
    "python.testing.pytestArgs": [
        "app/tests",
        "--config-file=pyproject.toml"
    ],
    "python.testing.unittestEnabled": false,
    "python.testing.pytestEnabled": true,
}
```

Afin de spéficier les variables d'environnement nécessaires pour les tests, vous devez également créer un fichier *.vscode/launch.json* avec la configuration suivante ou l'ajouter à votre fichier existant :

```json
{
    "version": "0.2.0",
    "configurations": [
        {
            "name": "Debug Test",
            "purpose": ["debug-test"],
            "type": "debugpy",
            "request": "launch",
            "program": "${file}",
            "args": ["--color=yes"],
            "env": {"CONFIG_FILE": "<path to config file>"},
            "console": "integratedTerminal",
        }
    ]
}
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
