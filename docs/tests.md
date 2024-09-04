## Tests

Vous pouvez vérifier le bon déploiement de votre API à l'aide en exécutant des tests unitaires.

1. Après avoir créer un fichier *config.yml*, lancez l'API en local

    ```bash
    uvicorn app.main:app --port 8080 --log-level debug --reload
    ```

2. Executez les tests unitaires

    ```bash
    PYTHONPATH=. pytest app/tests --base-url http://localhost:8080/v1 --api-key API_KEY
    ```