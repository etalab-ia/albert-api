<div id="toc"><ul align="center" style="list-style: none">
<summary><h1>Albert API</h1></summary>

![](https://img.shields.io/badge/version-0.0.3-yellow) ![](https://img.shields.io/badge/Python-3.12-green) ![Code Coverage](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/etalab-ia/albert-api/main/.github/badges/coverage.json)

<br>
<a href="https://github.com/etalab-ia/albert-api/blob/main/CHANGELOG.md"><b>Changelog</b></a> | <a href="https://albert.api.etalab.gouv.fr/documentation"><b>Documentation</b></a> | <a href="https://albert.api.etalab.gouv.fr/playground"><b>Playground</b></a> | <a href="https://albert.api.etalab.gouv.fr/status"><b>Status</b></a> | <a href="https://albert.api.etalab.gouv.fr/swagger"><b>Swagger</b></a> <br><br>
</ul></div>

## 👋 Présentation

Albert API, initiative d'**[Etalab](https://www.etalab.gouv.fr/)** dans le cadre du programme **[ALLiaNCE](https://alliance.numerique.gouv.fr/)**, est un framework open source d'IA générative comprenant : 

- une API gateway vers des clients API d'IA générative
- des fonctionnalités avancées comme du RAG (Retrieval Augmented Generation)

Ce framework, destiné à un environnement de production soumis à des contraintes de performance, a pour objectif d'être simple, léger et rapide tout en couvrant les fonctionnalités essentielles de l'état de l'art en la matière.

En se basant sur les conventions définies par OpenAI, Albert API expose des endpoints qui peuvent être appelés avec le [client officiel python d'OpenAI](https://github.com/openai/openai-python/tree/main). Ce formalisme permet une intégration aisée avec des bibliothèques tierces comme [Langchain](https://www.langchain.com/) ou [LlamaIndex](https://www.llamaindex.ai/).

## 🔑 Accès

Si vous êtes un organisme public, vous pouvez demander une clé d'accès à Albert API en remplissant le [formulaire sur le site ALLiaNCE](https://alliance.numerique.gouv.fr/albert/).

## 📫 API Gateway

L'API Albert permet d'être un proxy entre des clients API d'IA générative et d'assurer du load balancing entre les différents clients :

| Client                                                                                                  | Supported version | Supported model types                                        |
| ------------------------------------------------------------------------------------------------------- | ----------------- | ------------------------------------------------------------ |
| [OpenAI](https://platform.openai.com/docs/api-reference)                                                | latest            | • language<br>• embeddings<br>• reranking<br>• transcription |
| [vLLM](https://github.com/vllm-project/vllm)                                                            | v0.6.6.post1      | • language                                                   |
| [HuggingFace Text Embeddings Inference (TEI)](https://github.com/huggingface/text-embeddings-inference) | v1.5              | • embeddings<br>• reranking                                  |
| [Albert](https://github.com/etalab-ia/albert-api)                                                       | latest            | • language<br>• embeddings<br>• reranking<br>• transcription |


## ⚙️ Fonctionnalités avancées

- accès à un *vector store* avec [Elasticsearch](https://www.elastic.co/fr/products/elasticsearch) pour la recherche de similarité (lexicale, sémantique ou hybride) ou [Qdrant](https://qdrant.tech/) pour la recherche sémantique uniquement.
- authentification par clé API

## 🧩 Tutoriels

### Interface utilisateur (playground)

L'API Albert expose une interface utilisateur permettant de tester les différentes fonctionnalités, consultable [ici](https://albert.api.etalab.gouv.fr/playground).

### Converser avec un modèle de langage (chat memory)

L'API Albert permet de converser avec différents modèles de langage.

<a target="_blank" href="https://colab.research.google.com/github/etalab-ia/albert-api/blob/main/docs/tutorials/chat_completions.ipynb">
  <img src="https://colab.research.google.com/assets/colab-badge.svg" alt="Open In Colab"/>
</a>

### Accéder à plusieurs modèles de langage (multi models)

L'API Albert permet d'accéder à un ensemble de modèles de langage et d'embeddings grâce à une API unique.

<a target="_blank" href="https://colab.research.google.com/github/etalab-ia/albert-api/blob/main/docs/tutorials/models.ipynb">
  <img src="https://colab.research.google.com/assets/colab-badge.svg" alt="Open In Colab"/>
</a>

### Interroger des documents (search - retrieval augmented generation)

L'API Albert permet d'interroger des documents dans une base vectorielle. Ces documents sont classés dans des collections. Vous pouvez créer vos collections privées et utiliser les collections publiques déjà existantes. Enfin, une collection "internet" permet d'effectuer une recherche sur internet pour compléter la réponse du modèle.

<a target="_blank" href="https://colab.research.google.com/github/etalab-ia/albert-api/blob/main/docs/tutorials/retrieval_augmented_generation.ipynb">
  <img src="https://colab.research.google.com/assets/colab-badge.svg" alt="Open In Colab"/>
</a>

### Importer sa base de connaissances dans Albert (knowledge database)

L'API Albert permet d'importer sa base de connaissances dans une base vectorielle. Cette base vectorielle peut ensuite être utilisée pour faire de la RAG (Retrieval Augmented Generation).

<a target="_blank" href="https://colab.research.google.com/github/etalab-ia/albert-api/blob/main/docs/tutorials/import_knowledge_database.ipynb">
  <img src="https://colab.research.google.com/assets/colab-badge.svg" alt="Open In Colab"/>
</a>

### Transcription d'un fichier audio (audio transcriptions)

L'API Albert permet de transcrire un fichier audio à l'aide d'un modèle Whisper.

<a target="_blank" href="https://colab.research.google.com/github/etalab-ia/albert-api/blob/main/docs/tutorials/audio_transcriptions.ipynb">
  <img src="https://colab.research.google.com/assets/colab-badge.svg" alt="Open In Colab"/>
</a>

## 📚 Documentation

Vous trouverez ici des ressources de documentation : 
- [Documentation de l'API](https://albert.api.etalab.gouv.fr/documentation)
- [Documentation swagger de l'API](https://albert.api.etalab.gouv.fr/swagger)
- [Documentation technique de l'API](./docs)
- [Repository HuggingFace](https://huggingface.co/AgentPublic)

## 🧑‍💻 Contribuez au projet

Albert API est un projet open source, vous pouvez contribuer au projet en lisant notre [guide de contribution](./CONTRIBUTING.md).

## 🚀 Installation

Pour déployer l'API Albert sur votre propre infrastructure, suivez la [documentation](./docs/deployment.md).

### Quickstart

1. Complétez le fichier *[config.example.yml](./config.example.yml)* à la racine du dépot la configuration de vos API de modèles (voir la [documentation déploiement](./docs/deployment.md) pour plus d'informations).

2. Complétez le fichier *[compose.yml](./compose.yml)* à la racine du dépot avec les variables d'environnement nécessaires pour l'UI.

3. Déployez l'API avec Docker à l'aide du fichier [compose.yml](../compose.yml) à la racine du dépot.

  ```bash
  docker compose up --detach
  ```
