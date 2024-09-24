# Albert API
![](https://img.shields.io/badge/python-3.12-green) ![](https://img.shields.io/badge/vLLM-v0.5.5-blue) ![](https://img.shields.io/badge/HuggingFace%20Text%20Embeddings%20Inference-1.5-red)

Albert API est une API open source d'IA générative développée par Etalab. Elle permet d'être un proxy entre des modèles de langage et vos données. Elle aggrège les services suivants :
- [vLLM](https://github.com/vllm-project/vllm) pour la gestion des modèles de langage
- [HuggingFace Text Embeddings Inference](https://github.com/huggingface/text-embeddings-inference) pour la génération d'embeddings
- [Qdrant](https://qdrant.tech/) pour la recherche de similarité

### OpenAI conventions

En ce basant sur les conventions définies par OpenAI, l'API Albert expose des endpoints qui peuvent être appelés avec le [client officiel python d'OpenAI](https://github.com/openai/openai-python/tree/main). Ce formalisme permet d'intégrer facilement l'API Albert avec des bibliothèques tierces comme [Langchain](https://www.langchain.com/) ou [LlamaIndex](https://www.llamaindex.ai/).

## ⚙️ Fonctionnalités

### Converser avec un modèle de langage (chat memory)

<a target="_blank" href="https://colab.research.google.com/github/etalab-ia/albert-api/blob/main/docs/tutorials/chat_completions.ipynb">
  <img src="https://colab.research.google.com/assets/colab-badge.svg" alt="Open In Colab"/>
</a>

Albert API intègre nativement la mémorisation des messages pour les conversations sans surcharger d'arguments le endpoint `/v1/chat/completions` par rapport à la documentation d'OpenAI. Cela consiste à envoyer à chaque requête au modèle l'historique de la conversation pour lui fournir le contexte.

### Accéder à plusieurs modèles de langage (multi models)

<a target="_blank" href="https://colab.research.google.com/github/etalab-ia/albert-api/blob/main/docs/tutorials/models.ipynb">
  <img src="https://colab.research.google.com/assets/colab-badge.svg" alt="Open In Colab"/>
</a>

Grâce à un fichier de configuration (*[config.example.yml](./config.example.yml)*) vous pouvez connecter autant d'API de modèles que vous le souhaitez. L'API Albert se charge de mutualiser l'accès à tous ces modèles dans une unique API. Vous pouvez obtenir la liste des différents modèles accessibles en appelant le endpoint `/v1/models`.

### Interroger des documents (RAG)

<a target="_blank" href="https://colab.research.google.com/github/etalab-ia/albert-api/blob/main/docs/tutorials/retrival_augmented_generation.ipynb">
  <img src="https://colab.research.google.com/assets/colab-badge.svg" alt="Open In Colab"/>
</a>

## 🧑‍💻 Contribuez au projet

Albert API est un projet open source, vous pouvez contribuez au projet, veuillez lire notre [guide de contribution](./CONTRIBUTING.md).