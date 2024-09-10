# Albert API

## Fonctionnalités

### OpenAI conventions

En ce basant sur les conventions définies par OpenAI, l'API Albert expose des endpoints qui peuvent être appelés avec le [client officiel python d'OpenAI](https://github.com/openai/openai-python/tree/main).

Ce formalisme permet d'intégrer facilement l'API Albert avec des bibliothèques tierces comme [Langchain](https://www.langchain.com/) ou [LlamaIndex](https://www.llamaindex.ai/).

### Converser avec un modèle de langage (chat memory)

<a target="_blank" href="https://colab.research.google.com/github/etalab-ia/albert-api/blob/main/docs/tutorials/chat_completions.ipynb">
  <img src="https://colab.research.google.com/assets/colab-badge.svg" alt="Open In Colab"/>
</a>

Albert API intègre nativement la mémorisation des messages pour les conversations sans surcharger d'arguments le endpoint `/v1/chat/completions` par rapport à la documentation d'OpenAI. Cela consiste à envoyer à chaque requête au modèle l'historique de la conversation pour lui fournir le contexte.

### Accéder à plusieurs modèles de langage (multi models)

<a target="_blank" href="https://colab.research.google.com/github/etalab-ia/albert-api/blob/main/docs/tutorials/models.ipynb">
  <img src="https://colab.research.google.com/assets/colab-badge.svg" alt="Open In Colab"/>
</a>

Grâce à un fichier de configuration (*[config.example.yml](./config.example.yml)*) vous pouvez connecter autant d'API de modèles que vous le souhaitez. L'API Albert se charge de mutualiser l'accès à tous ces modèles dans une unique API. Vous pouvez constater les différents modèles accessibles en appelant le endpoint `/v1/models`.

### Fonctionnalités avancées (tools)

Les tools sont une fonctionnalité définie par OpenAI que l'on surcharge dans le cas de l'API Albert pour permettre de configurer des tâches spéficiques comme du RAG ou la génération de résumé. Vous pouvez appelez le endpoint `/tools` pour voir la liste des tools disponibles.

![](./docs/assets/chatcompletion.png)

#### Interroger des documents (RAG)

<a target="_blank" href="https://colab.research.google.com/github/etalab-ia/albert-api/blob/main/docs/tutorials/retrival_augmented_generation.ipynb">
  <img src="https://colab.research.google.com/assets/colab-badge.svg" alt="Open In Colab"/>
</a>

#### Résumer un document (summarize)

<a target="_blank" href="https://colab.research.google.com/github/etalab-ia/albert-api/blob/main/docs/tutorials/summarize.ipynb">
  <img src="https://colab.research.google.com/assets/colab-badge.svg" alt="Open In Colab"/>
</a>
