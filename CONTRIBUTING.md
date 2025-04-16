# Contributions

Pour contribuer au projet, merci de suivre les instructions suivantes.

# Développement en environnement Docker

> ⚠️ **Attention : Vous devez disposer d'une API de modèle de language.**

1. Créez un fichier *config.yml* à partir du fichier d'exemple de configuration *[config.example.yml](./config.example.yml)* avec vos modèles.

    Pour plus d'information sur le déploiement des services, veuillez consulter la [documentation dédiée](./docs/deployment.md).

    > [!NOTE] Le fichier de configuration pour exécuter les tests est [config.test.yml](./.github/config.test.yml). Vous pouvez vous en inspirer pour configurer votre propre fichier de configuration.

2. Lancer le docker compose de développement avec le mode watch :

    ```bash
    docker compose --file compose.dev.yml up --watch
    ```

    > [!NOTE] L'API et le playground seront disponibles respectivement sur les ports 8000 et 8501. Pour vous connecter au playground la première fois utilisez le login *master* et le mot de passe *changeme* (définit dans le fichier de configuration).

# Développement hors environnement Docker

1. Créez un fichier *config.yml* à partir du fichier d'exemple de configuration *[config.example.yml](./config.example.yml)* avec vos modèles.

    Pour plus d'information sur le déploiement des services, veuillez consulter la [documentation dédiée](./docs/deployment.md).

    > [!NOTE] Le fichier de configuration pour exécuter les tests est [config.test.yml](./.github/config.test.yml). V

2. Instanciez les dépendances

    ```bash
    docker compose up --detach # run the databases

    pip install ".[app,ui,dev,test]" # install the dependencies

    alembic -c app/alembic.ini upgrade head # create the API tables
    alembic -c ui/alembic.ini upgrade head # create the Playground tables
    ```

3. Lancez l'API

    ```bash
    uvicorn app.main:app --port 8000 --log-level debug --reload # run the API
    ```

4. Lancez le playground

    Dans un autre terminal, lancez le playground avec la commande suivante :

    ```bash
    streamlit run ui/chat.py --server.port 8501 --browser.gatherUsageStats false --theme.base light # run the playground
    ```

    Pour vous connecter au playground la première fois utilisez le login *master* et le mot de passe *changeme* (définit dans le fichier de configuration).

# Modifications de la structure des bases de données SQL

## Modifications du fichier [`app/sql/models.py`](./app/sql/models.py)

Si vous avez modifié les tables de la base de données de l'API dans le fichier [models.py](./app/sql/models.py), vous devez créer une migration Alembic avec la commande suivante :

```bash
alembic -c app/alembic.ini revision --autogenerate -m "message"
```

Puis appliquez la migration avec la commande suivante :

```bash
alembic -c app/alembic.ini upgrade head
```

## Modifications du fichier [`ui/sql/models.py`](./ui/sql/models.py)

Si vous avez modifié les tables de la base de données de l'UI dans le fichier [models.py](./ui/sql/models.py), vous devez créer une migration Alembic avec la commande suivante :

```bash
alembic -c ui/alembic.ini revision --autogenerate -m "message"
```

Puis appliquez la migration avec la commande suivante :

```bash
alembic -c ui/alembic.ini upgrade head
```

# Tests

Merci, avant chaque pull request, de vérifier le bon déploiement de votre API en exécutant les tests prévus à cet effet. Pour exécuter ces tests à la racine du projet, exécutez la commande suivante :

```bash
CONFIG_FILE=./.github/config.test.yml PYTHONPATH=. pytest --config-file=pyproject.toml
```

> [!NOTE] Le fichier de configuration pour exécuter les tests est [config.test.yml](./.github/config.test.yml). Vous pouvez le modifier pour exécuter les tests sur votre machine.

Pour mettre à jour les snapshots, exécutez la commande suivante :

```bash
PYTHONPATH=. pytest --config-file=pyproject.toml --snapshot-update
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

Merci de bien vouloir installer les hooks de pre-commit :

```bash
pip install ".[dev]"
pre-commit install
```

Ruff s'exécutera automatiquement à chaque commit.

# Commit 

Merci de respecter la convention suivante pour vos commits :

```
[doc|feat|fix](*) commit object (in english)

# example
feat(collections): collection name retriever
```

*Le thème est optionnel et doit correspondre à un thématique de la code base (deploy, collections, models, ...).

