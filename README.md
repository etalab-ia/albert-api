<div id="toc">
  <ul align="center" style="list-style: none">
    <summary><h1>🚀 Albert API</h1></summary>

*French version below*

**Enterprise-ready Generative AI API Gateway | Open Source | Sovereign Infrastructure**

**Developed by the French Government 🇫🇷**

[![Code Coverage](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/etalab-ia/albert-api/refs/heads/main/.github/badges/coverage.json)](https://github.com/etalab-ia/albert-api)

[**Documentation**](https://albert.api.etalab.gouv.fr/documentation) | [**Playground**](https://albert.api.etalab.gouv.fr/playground) | [**API Status**](https://albert.api.etalab.gouv.fr/status) | [**Swagger**](https://albert.api.etalab.gouv.fr/swagger)

  </ul>
</div>


## 🚀 Quickstart

### Run Albert-API with basic functionalities (docker)
Albert-API is configured by default to launch via Docker the API, the playground and a PostgreSQL database, and to connect to a small model made available for free. Simply run:
```bash
make docker-compose-quickstart-up
```

To stop the services, run
```bash
make docker-compose-quickstart-down
```

### Configure Albert-API
Albert-API supports OpenAI and Albert-API models. To configure them, run:
```bash
cp config.example.yml config.yml
```

And modify the `models` section in the `config.yml` file:

```yaml
models:
  - id: albert-large
    type: text-generation
    owned_by: test
    aliases: ["mistralai/Mistral-Small-3.1-24B-Instruct-2503"]
    clients:
      - model: mistralai/Mistral-Small-3.1-24B-Instruct-2503
        type: albert
        args:
          api_url: ${ALBERT_API_URL:-https://albert.api.etalab.gouv.fr}
          api_key: ${ALBERT_API_KEY}
          timeout: 120
  - id: my-language-model
    type: text-generation
    clients:
      - model: gpt-3.5-turbo
        type: openai
        params:
          total: 70
          active: 70
          zone: WOR
        args:
          api_url: https://api.openai.com
          api_key: ${OPENAI_API_KEY}
          timeout: 60
```
The API keys can be defined directement in the `config.yml` file or in a `.env` file

```bash
cp .env.example .env

echo 'ALBERT_API_KEY=my_albert_api_key' >> .env
echo 'OPENAI_API_KEY=my_openai_api_key' >> .env
```

Finally, run the application:
```bash
make docker-compose-albert-api-up
```

To stop the application, run:
```bash
make docker-compose-albert-api-down
```


## Running locally

### Prerequisites
- Python 3.8+
- Docker and Docker Compose

### Installation

#### 1. Installing dependencies

```bash
make install
```

#### 2. Configuration

Albert-API supports OpenAI and Albert-API models, defined in the `config.yml` file :
```bash
cp config.example.yml config.yml
```

And modify the `models` section in the `config.yml` file:

```yaml
models:
  - id: albert-large
    type: text-generation
    owned_by: test
    aliases: ["mistralai/Mistral-Small-3.1-24B-Instruct-2503"]
    clients:
      - model: mistralai/Mistral-Small-3.1-24B-Instruct-2503
        type: albert
        args:
          api_url: ${ALBERT_API_URL:-https://albert.api.etalab.gouv.fr}
          api_key: ${ALBERT_API_KEY}
          timeout: 120
  - id: my-language-model
    type: text-generation
    clients:
      - model: gpt-3.5-turbo
        type: openai
        params:
          total: 70
          active: 70
          zone: WOR
        args:
          api_url: https://api.openai.com
          api_key: ${OPENAI_API_KEY}
          timeout: 60
```
The API keys can be defined directement in the `config.yml` file or in a `.env` file

```bash
cp .env.example .env

echo 'ALBERT_API_KEY=my_albert_api_key' >> .env
echo 'OPENAI_API_KEY=my_openai_api_key' >> .env
```

### Running

#### Option 1: Full launch with Docker

```bash
# Start all services (API, playground and external services)
make docker-compose-albert-api-up
# Stop all services
make docker-compose-albert-api-down
```

#### Option 2: Local development

```bash
# 1. Start only external services (Redis, Qdrant, PostgreSQL, MCP Bridge)
make docker-compose-services-up

# 2. Launch the API (in one terminal)
make run-api

# 3. Launch the user interface (in another terminal)
make run-ui
```

## 📫 API Gateway

## 🔥 Why Albert API?

Albert API is an **enterprise-ready open-source gateway** for deploying **generative AI models** on your infrastructure:

* 🚦 **Robust API Gateway:** Load balancing, authentication, and seamless integration with OpenAI, vLLM, HuggingFace TEI.
* 📚 **Advanced Features:** Built-in Retrieval-Augmented Generation (RAG), OCR, audio transcription, and more.
* 🌐 **Open Standards:** Compatible with OpenAI APIs, LangChain, and LlamaIndex.
* 🛠️ **Deployment Flexibility:** Host generative AI securely on your own infrastructure, ensuring full data sovereignty.

## 🎯 Key Features

### API Gateway

* **Unified Access:** Single API gateway for multiple generative AI model backends:

  * **OpenAI** (Language, Embeddings, Reranking, Transcription)
  * **vLLM** (Language)
  * **HuggingFace TEI** (Embeddings, Reranking)

### Advanced AI Capabilities

* **RAG Integration:** Efficiently query vector databases using Elasticsearch or Qdrant.
* **Audio & Vision:** Transcribe audio (Whisper) and perform OCR on PDF documents.
* **Enhanced Security:** Built-in API key authentication.

## 📊 Comparison

| Feature              | Albert API ✅ | LiteLLM   | OpenRouter | OpenAI API |
| -------------------- | ------------ | --------- | ---------- | ---------- |
| Fully Open Source    | ✔️           | Partially | ❌          | ❌          |
| Data Sovereignty     | ✔️           | ✔️        | ❌          | ❌          |
| Multiple AI Backends | ✔️           | ✔️        | ✔️         | ❌          |
| Built-in RAG         | ✔️           | ❌         | ❌          | ❌          |
| Built-in OCR         | ✔️           | ❌         | ❌          | ❌          |
| Audio Transcription  | ✔️           | ❌         | ❌          | ✔️         |
| Flexible Deployment  | ✔️           | ✔️        | ❌          | ❌          |
| OpenAI Compatibility | ✔️           | ✔️        | ✔️         | ✔️         |

## 🚀 Quickstart

Deploy Albert API quickly on your own infrastructure:

* [Deployment Guide](./docs/deployment.md)

## 📘 Tutorials & Guides

Explore practical use cases:

* [**Chat Completions**](https://colab.research.google.com/github/etalab-ia/albert-api/blob/main/docs/tutorials/chat_completions.ipynb)
* [**Multi-Model Access**](https://colab.research.google.com/github/etalab-ia/albert-api/blob/main/docs/tutorials/models.ipynb)
* [**Retrieval-Augmented Generation (RAG)**](https://colab.research.google.com/github/etalab-ia/albert-api/blob/main/docs/tutorials/retrieval_augmented_generation.ipynb)
* [**Knowledge Database Import**](https://colab.research.google.com/github/etalab-ia/albert-api/blob/main/docs/tutorials/import_knowledge_database.ipynb)
* [**Audio Transcriptions**](https://colab.research.google.com/github/etalab-ia/albert-api/blob/main/docs/tutorials/audio_transcriptions.ipynb)
* [**PDF OCR**](https://colab.research.google.com/github/etalab-ia/albert-api/blob/main/docs/tutorials/pdf_ocr.ipynb)

## 🤝 Contribute

Albert API thrives on open-source contributions. Join our community!

* [Contribution Guide](./CONTRIBUTING.md)

---

# 🇫🇷 Albert API (version française)

**API open source pour modèles d'IA générative | Infrastructure souveraine**

Albert API, porté par l'[OPI de la DINUM](https://www.numerique.gouv.fr/dinum/), est le service d'IA générative de référence de l'État français, homologué pour des traitements sécurisés. Il propose une solution prête pour la production destinée à l’hébergement souverain et performant d’IA génératives avancées sur votre infrastructure.

## Points forts

* 🔐 Sécurité et souveraineté des données
* 🧩 API unique compatible OpenAI, vLLM et HuggingFace
* 🔎 Recherche avancée par RAG et vector stores

Consultez la [documentation](https://albert.api.etalab.gouv.fr/documentation) ou déployez rapidement votre instance via le [guide de déploiement](./docs/deployment.md).

[Contribuez au projet !](./CONTRIBUTING.md)
