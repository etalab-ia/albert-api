<div id="toc"><ul align="center" style="list-style: none">
<summary><h1>Albert API</h1></summary>

![](https://img.shields.io/badge/version-alpha-yellow) ![](https://img.shields.io/badge/Python-3.12-green) ![](https://img.shields.io/badge/vLLM-v0.6.3.post1-blue) ![](https://img.shields.io/badge/HuggingFace%20Text%20Embeddings%20Inference-1.5-red)<br>
<a href="https://github.com/etalab-ia/albert-api/blob/main/CHANGELOG.md"><b>Changelog</b></a> | <a href="https://albert.api.etalab.gouv.fr/documentation"><b>Documentation</b></a> | <a href="https://albert.api.etalab.gouv.fr/status"><b>Status</b></a> | <a href="https://albert.api.etalab.gouv.fr/swagger"><b>Swagger</b></a> <br><br>
</ul></div>

Albert API est une initiative d'[Etalab](https://www.etalab.gouv.fr/). Il s'agit d'une API open source d'IA générative développée par Etalab. Elle permet d'être un proxy entre des modèles de langage et vos données. Elle agrège les services suivants :
- servir des modèles de langage avec [vLLM](https://github.com/vllm-project/vllm)
- servir des modèles d'embeddings avec [HuggingFace Text Embeddings Inference](https://github.com/huggingface/text-embeddings-inference)
- servir des modèles de reconnaissance vocale avec [Whisper OpenAI API](https://github.com/etalab-ia/whisper-openai-api)
- accès un *vector store* avec [Qdrant](https://qdrant.tech/) pour la recherche de similarité

En se basant sur les conventions définies par OpenAI, l'API Albert expose des endpoints qui peuvent être appelés avec le [client officiel python d'OpenAI](https://github.com/openai/openai-python/tree/main). Ce formalisme permet d'intégrer facilement l'API Albert avec des bibliothèques tierces comme [Langchain](https://www.langchain.com/) ou [LlamaIndex](https://www.llamaindex.ai/).

## ⚙️ Fonctionnalités

### Interface utilisateur (playground)

L'API Albert expose une interface utilisateur permettant de tester les différentes fonctionnalités, consultable ici [ici](https://albert.api.etalab.gouv.fr).

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

### Interroger vos documents (RAG)

L'API Albert permet d'interroger des documents dans une base vectorielle. Ces documents sont classés dans des collections. Vous pouvez créer vos collections privées et utiliser les collections publiques déjà existantes. Enfin, une collection "internet" permet d'effectuer une recherche sur internet pour compléter la réponse du modèle.

<a target="_blank" href="https://colab.research.google.com/github/etalab-ia/albert-api/blob/main/docs/tutorials/retrival_augmented_generation.ipynb">
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

## 🧑‍💻 Contribuez au projet

Albert API est un projet open source, vous pouvez contribuer au projet en lisant notre [guide de contribution](./CONTRIBUTING.md).

## 🚀 Installation

Pour déployer l'API Albert sur votre propre infrastructure, suivez la [documentation](./docs/deployment.md).
