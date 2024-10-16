<div align="center">

# Albert API

![](https://img.shields.io/badge/python-3.12-green) ![](https://img.shields.io/badge/vLLM-v0.5.5-blue) ![](https://img.shields.io/badge/HuggingFace%20Text%20Embeddings%20Inference-1.5-red)<br>
<a href="https://albert.api.etalab.gouv.fr/docs"><b>Documentation</b></a> | <a href="https://github.com/etalab-ia/albert-api/blob/main/CHANGELOG.md"><b>Changelog</b></a> | <a href="https://huggingface.co/AgentPublic"><b>HuggingFace</b></a>
<br><br>
</div>

Albert API est une initiative d'[Etalab](https://www.etalab.gouv.fr/). Il s'agit d'une API open source d'IA générative développée par Etalab. Elle permet d'être un proxy entre des modèles de langage et vos données. Elle agrège les services suivants :
- servir des modèles de langage avec [vLLM](https://github.com/vllm-project/vllm)
- servir des modèles d'embeddings avec [HuggingFace Text Embeddings Inference](https://github.com/huggingface/text-embeddings-inference)
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

## 🧑‍💻 Contribuez au projet

Albert API est un projet open source, vous pouvez contribuer au projet en lisant notre [guide de contribution](./CONTRIBUTING.md).

## 🚀 Installation

Pour déployer l'API Albert sur votre propre infrastructure, suivez la [documentation](./docs/deployment.md).

