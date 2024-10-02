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

## [Alpha] - 2024-10-01

- 💣 Les collections sont appelées dorénavant par leur collection ID et non plus par leur nom
- 💣 Le endpoint POST `/v1/files` ne créer plus de collection si elle n'existe pas
- 🎉 Le endpoint POST `/v1/files` accepte maintenant tous les paramètres du chunking
- 🎉 Ajout de rôles utilisateur et admin pour la création de collection publiques
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
