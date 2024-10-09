# Changelog

Tous les changements notables de l'application sont documentés dans ce fichier.

**Légende :**
- 💣 Breaking changes
- 🎉 New features
- 🐛 Bug fixes
- 📚 Documentation
- 🧪 Tests
- 🤖 CI/CD
- 🔄 Refactoring
- ❌ Deprecated

## [Alpha] - 2024-10-09

- 🎉 Ajout d'un status du modèle dans le retour du endpoint GET `/v1/models`. Ce status permet de vérifier si le modèle est disponible ou non.

## [Alpha] - 2024-10-07

- 💣 Création de la notion de Document, objet intermédiaire entre un fichier et une collection de chunks. Ajout des endpoints GET `/v1/documents` et DELETE `/v1/documents` pour solutionner le problème de limite de taille de requête.
- ❌ Suppression de l'endpoint POST `/v1/chunks` pour récupérer plusieurs chunks de différents documents en une seule requête.
- ❌ Suppression des endpoint GET `/v1/files` et DELETE `/v1/files`
- 🎉 Ajout de la possibilité de récupérer les documents d'une collection
- 🎉 Ajout de la possibilité de supprimer un document d'une collection
- 🎉 Ajout de la possibilité de récupérer les chunks d'un document
- 🎉 Ajout d'un chunker "NoChunker" qui permet de considérer le fichier en entier comme un chunk
- 🐛 Les exceptions sont remontées de manière plus claire dans l'API
- 🐛 Les modèles d'embeddings font remontées une erreur lorsque le context fourni est trop grand
- 🔄 Meilleur cloisement des dépendances techniques du projet dans des classes distinctes
- 🧪 Ajout de tests unitaires pour les endpoints *documents* et *chunks*
- 🧪 Ajout de la configuration pytest dans le fichier `pyproject.toml`

## [Alpha] - 2024-10-01

- 💣 Les collections sont appelées dorénavant par leur collection ID et non plus par leur nom
- 💣 Le endpoint POST `/v1/files` ne créer plus de collection si elle n'existe pas
- 🎉 Le endpoint POST `/v1/files` accepte maintenant tous les paramètres du chunking
- 🎉 Ajout de rôles utilisateur et admin pour la création de collection publiques
- 🎉 Ajout d'un middleware pour limiter la taille des requêtes d'upload de fichiers
- 🎉 Ajout de la collection "internet" qui permet d'effectuer une recherche sur internet pour compléter la réponse du modèle
- 🎉 Affichage des sources dans le chat UI
- 🐛 Les erreurs sont remontées de manière plus claire dans l'upload de fichiers
- 🔄 Les modèles pydantic des endpoints sont harmonisés et sont plus restrictifs
- 🔄 Les clients sont instanciés par une classe ClientsManager
- 🧪 Ajout de tests unitaires
- 📚 Ajout d'un tutoriel pour l'import de bases de connaissances  
- ❌ Les fichiers Docx ne sont plus supportés dans l'upload de fichiers
- ❌ Suppression de l'upload de plusieurs fichiers dans une seule requête
- ❌ Suppression de l'endpoint POST `/v1/chunks` pour récupérer plusieurs chunks en une seule requête
