<div id="toc">
  <ul align="center" style="list-style: none">

# OpenGateLLM

[![Version](https://img.shields.io/github/v/release/etalab-ia/OpenGateLLM?color=orange&label=version)](https://github.com/etalab-ia/OpenGateLLM/releases) 
[![Code Coverage](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/etalab-ia/OpenGateLLM/refs/heads/main/.github/badges/coverage.json)](https://github.com/etalab-ia/OpenGateLLM)
[![License](https://img.shields.io/github/license/etalab-ia/OpenGateLLM?color=red&label=license)](https://github.com/etalab-ia/OpenGateLLM/blob/main/LICENSE)
[![French version](https://img.shields.io/badge/🇫🇷-French%20version-blue)](./docs/README_fr.md)

### *✨ One place to serve your models, manage usage, and build production-ready products on top 

— with RAG, OCR, Whisper & more. ✨*

[**API Reference**](https://albert.api.etalab.gouv.fr/documentation) | [**Swagger**](https://albert.api.etalab.gouv.fr/swagger)

  </ul>
</div>

## 🔥 Why OpenGateLLM?

- 🌐 **OpenAI standards**: based on OpenAI API conventions. Easy to use with OpenAI SDKs, LangChain, LlamaIndex, etc.
- 🚦 **Robust API Gateway:** Load balancing, authentication, and seamless integration with OpenAI, vLLM, HuggingFace TEI.
- 📖 **Open Source**: developed by the French Government, fully open-source forever.
- ⚙️ **Production-ready**: ready to serve your models in production.
- 📚 **Full stack genAI API:** Built-in Retrieval-Augmented Generation (RAG), OCR, audio transcription, and more.
- ✍️ **High code standards**

## 🎯 Key Features

### API Gateway: supported providers

| Provider | Supported endpoints |
| -------- | ------------------- |
| Albert API (French Public Administration)   | Language, Embeddings, Reranking, Transcription |
| OpenAI   | Language, Embeddings, Reranking, Transcription |
| vLLM     | Language |
| HuggingFace TEI | Embeddings, Reranking |

### Advanced AI Capabilities

* **RAG Integration:** Efficiently query vector databases using Elasticsearch or Qdrant.
* **Audio & Vision:** Transcribe audio (Whisper) and perform OCR on PDF documents.
* **Enhanced Security:** Built-in API key authentication.

## 📊 Comparison

| Feature              | OpenGateLLM ✅ | LiteLLM   | OpenRouter | OpenAI API |
| -------------------- | ------------ | --------- | ---------- | ---------- |
| Fully Open Source    | ✔️ | ❌ | ❌ | ❌ |
| Data Sovereignty     | ✔️ | ✔️ | ❌ | ❌ |
| Multiple AI Backends | ✔️ | ✔️ | ✔️ | ❌ |
| Built-in RAG         | ✔️ | ❌ | ❌ | ❌ |
| Built-in OCR         | ✔️ | ❌ | ❌ | ❌ |
| Audio Transcription  | ✔️ | ❌ | ❌ | ❌ |
| Flexible Deployment  | ✔️ | ✔️ | ❌ | ❌ |
| OpenAI Compatibility | ✔️ | ✔️ | ✔️ | ❌ |

## 📘 Tutorials & Guides

Explore practical use cases:

* [**Chat Completions**](https://colab.research.google.com/github/etalab-ia/opengatellm/blob/main/docs/tutorials/chat_completions.ipynb)
* [**Multi-Model Access**](https://colab.research.google.com/github/etalab-ia/opengatellm/blob/main/docs/tutorials/models.ipynb)
* [**Retrieval-Augmented Generation (RAG)**](https://colab.research.google.com/github/etalab-ia/opengatellm/blob/main/docs/tutorials/retrieval_augmented_generation.ipynb)
* [**Knowledge Database Import**](https://colab.research.google.com/github/etalab-ia/opengatellm/blob/main/docs/tutorials/import_knowledge_database.ipynb)
* [**Audio Transcriptions**](https://colab.research.google.com/github/etalab-ia/opengatellm/blob/main/docs/tutorials/audio_transcriptions.ipynb)
* [**PDF OCR**](https://colab.research.google.com/github/etalab-ia/opengatellm/blob/main/docs/tutorials/pdf_ocr.ipynb)

## 🚀 Quickstart

Deploy OpenGateLLM quickly with Docker connected to own free model and start using it:

```bash
make quickstart
```
Test the API:

```bash 
curl -X POST "http://localhost:8080/v1/chat/completions" \
-H "Content-Type: application/json" \
-H "Authorization: Bearer changeme" \
-d '{"model": "albert-testbed", "messages": [{"role": "user", "content": "Hello, how are you?"}]}'
```
The default master API key is `changeme`.

### User interface

A user interface is available at: http://localhost:8081/playground

User: master
Password: changeme

### Create a first user

```bash
make create-user
```

### Configure your models and add features

With configuration file, you can connect to your own models and add addtionnal services to OpenGateLLM. 
Start by creating a configuration file and a .env dedicated:

```bash
cp --update=none config.example.yml config.yml
cp --update=none .env.example .env
```

Check the [configuration documentation](./docs/configuration.md) to configure your configuration file.

Vou can then set your environment variables in .env according to your needs.

You can run the services you need by running:
```bash
docker compose --env-file .env up <services_you_need> --detach 
```

For instance:
```bash
docker compose --env-file .env up api playground postgres redis elasticsearch secretiveshell --detach 
```

### Alternative: use kubernetes

You can check our helmchart and instructions here: [https://github.com/etalab-ia/albert-api-helm](https://github.com/etalab-ia/opengatellm-helm)


## 🤝 Contribute

This project exists thanks to all the people who contribute. OpenGateLLM thrives on open-source contributions. Join our community!

* [Contribution Guide](./CONTRIBUTING.md)

## Sponsors

<div id="toc">
  <ul align="center" style="list-style: none">
<a href="https://www.numerique.gouv.fr/numerique-etat/dinum/" ><img src="./docs/assets/dinum_logo.png" alt="DINUM logo" width="300" style="margin-right: 40px"></a>
<a href="https://www.centralesupelec.fr"><img src="./docs/assets/centralsupelec_logo.png" alt="CentraleSupélec logo" width="200" style="margin-right: 40px"></a>
  </ul>
</div>
