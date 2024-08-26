## Tests

Vous pouvez vérifier le bon déploiement de votre API à l'aide en exécutant des tests unitaires : 

```bash
cd app/tests
CONFIG_FILE="../../config.yml" pytest test_models.py
CONFIG_FILE="../../config.yml" pytest test_chat.py
```