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

# Développement en environnement Docker

1. Editez le fichier d'exemple de configuration *[config.example.yml](./config.example.yml)* avec vos modèles de langage et d'embeddings.

2. Editez le fichier *[compose.dev.yml](./compose.dev.yml)* avec les variables d'environnement nécessaires pour l'UI.

    Pour plus d'information sur le déploiement des services, veuillez consulter la [documentation dédiée](./docs/deployment.md).


3. Pour développer dans un environnement Docker, lancer le docker compose de développement avec le mode watch :

    ```bash
    docker compose --file compose.dev.yml up --watch
    ```

L'API et l'UI seront disponibles respectivement sur les ports 8000 et 8501.

# Développement hors environnement Docker

1. Dans un environnement virtuel Python, installez les packages Python présents dans le fichier *[pyproject.toml](./pyproject.toml)*

    ```bash 
    pip install ".[ui,app,dev,test]"
    pre-commit install
    ```

2. Créez un fichier *config.yml* à partir du fichier d'exemple de configuration *[config.example.yml](./config.example.yml)* avec vos modèles de langage et d'embeddings.
   
    Pour plus d'information sur le déploiement des services, veuillez consulter la [documentation dédiée](./docs/deployment.md).


3. Lancez l'API en local

    ```bash
    uvicorn app.main:app --port 8000 --log-level debug --reload
    ```

4. Exportez les variables d'environnement nécessaires pour l'UI.
   
    ```bash
    export BASE_URL=http://localhost:8000/v1
    export DOCUMENTS_EMBEDDINGS_MODEL=
    ```

5. Lancez l'UI en local

    ```bash
    python -m streamlit run ui/chat.py --server.port 8501 --browser.gatherUsageStats false --theme.base light
    ```

# Tests

Merci, avant chaque pull request, de vérifier le bon déploiement de votre API en exécutant les tests prévus à cet effet. Pour exécuter ces tests à la racine du projet, exécutez la commande suivante :
    
```bash
CONFIG_FILE=<path to config file> PYTHONPATH=. pytest --config-file=pyproject.toml --api-key-user <api key user> --api-key-admin <api key admin>
```

Pour n'exécuter qu'une partie des tests, par exemple les test *audio*, exécutez la commande suivante :

```bash
CONFIG_FILE=<path to config file> PYTHONPATH=. pytest app/tests/test_audio.py --config-file=pyproject.toml --api-key-user <api key user> --api-key-admin <api key admin>
```

Pour mettre à jour les snapshots, exécutez la commande suivante :

```bash
CONFIG_FILE=<path to config file> PYTHONPATH=. pytest --config-file=pyproject.toml --api-key-user <api key user> --api-key-admin <api key admin> --update-snapshots
```

## Configurer les tests dans VSCode

Pour utiliser le module testing de VSCode, veuillez la configuration suivante dans votre fichier *.vscode/settings.json* :

```json
{
    "python.testing.pytestArgs": [
        "app/tests",
        "--config-file=pyproject.toml",
        "--api-key-user=<api key user>",
        "--api-key-admin=<api key admin>"
    ],
    "python.testing.unittestEnabled": false,
    "python.testing.pytestEnabled": true
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

Pour lancer les notebooks en local :

```bash
pip install ".[dev]"
jupyter notebook docs/tutorials/
```

# Linter

Le linter du projet est [Ruff](https://beta.ruff.rs/docs/configuration/). Les règles de formatage spécifiques au projet sont dans le fichier *[pyproject.toml](./pyproject.toml)*.

## Configurer Ruff avec pre-commit

1. Installez les hooks de pre-commit

    ```bash
    pip install ".[dev]"
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
