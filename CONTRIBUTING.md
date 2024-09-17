# Contributions

Pour contribuer au projet, merci de suivre les instructions suivantes.

# Commit 

Merci de respecter la convention suivante pour vos commits : 

```
[doc|feat|fix](*) commit object (in english)

# example
feat(collections): collection name retriever
```

&ast;*Le thème est optionnel et doit correspondre à un thématique de la code base (deploy, collections, models, ...).

# Packages

1. Installez [libmagic](https://man7.org/linux/man-pages/man3/libmagic.3.html)

2. Dans un environnement virtuel Python, installez les packages Python présents dans le fichier *[pyproject.toml](./pyproject.toml)*

  ```bash 
  pip install ".[ui,app]"
  ```

# Tests

Merci avant chaque pull request, de vérifier le bon déploiement de votre API à l'aide en exécutant des tests unitaires.

1. Après avoir créer un fichier *config.yml*, lancez l'API en local

    ```bash
    uvicorn app.main:app --port 8080 --log-level debug --reload
    ```

2. Executez les tests unitaires

    ```bash
    PYTHONPATH=. pytest -v --exitfirst app/tests --base-url http://localhost:8080/v1 --api-key API_KEY
    ```

# Linter

Le linter du projet est [Ruff](https://beta.ruff.rs/docs/configuration/). Les règles de formatages spécifiques au projet sont dans le fichier *[pyproject.toml](./pyproject.toml)*.

## Configurer Ruff sur VSCode

1. Installez l'extension *Ruff* (charliermarsh.ruff) dans VSCode
2. Configurez le linter Ruff dans VSCode pour utiliser le fichier *[pyproject.toml](./pyproject.toml)*

    A l'aide de la commande palette de VSCode (⇧⌘P), recherchez et sélectionnez *Preferences: Open User Settings (JSON)*.

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

    ⚠️ **Attention** : Assurez vous que le fichier *[pyproject.toml](./app/pyproject.toml)* est bien spécifié dans la configuration.

3. **Pour exécuter le linter, utilisez la commande palette de VSCode (⇧⌘P) depuis le fichier sur lequel vous voulez l'exécuter, et recherchez et sélectionnez *Ruff: Format document* et *Ruff: Format imports*.**
