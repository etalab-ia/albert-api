# Changelog

Tous les changements notables de l'application sont documentés dans ce fichier.

**Légende :**
- 💣 Breaking changes
- 🎉 New features
- 🐛 Bug fixes
- 📚 Documentation
- 🧪 Tests
- 🚀 Deployment
- 🤖 CI/CD
- 🔄 Refactoring
- ❌ Deprecated

## [Alpha] - 2024-10-01

- 💣 Les collections sont appelées dorénavant par leur collection ID et non plus par leur nom
- 🎉 Ajout de rôles utilisateur et admin pour la création de collection publiques
- 🎉 Ajout de la collection "internet" qui permet d'effectuer une recherche sur internet pour compléter la réponse du modèle
- ❌ Les fichiers Docx ne sont plus supportés dans l'upload de fichiers
- 🐛 Les erreurs sont remontées de manière plus claire dans l'upload de fichiers
- 🧪 Ajout de tests unitaires
- 📚 Ajout d'un tutoriel pour l'import de bases de connaissances
- ❌ Suppression de l'upload de plusieurs fichiers dans une seule requête
- ❌ Suppression de l'endpoint POST `/v1/chunks` pour récupérer plusieurs chunks en une seule requête

