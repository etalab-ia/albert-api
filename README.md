<div id="toc">
  <ul align="center" style="list-style: none">

# Albert API

[![Version](https://img.shields.io/github/v/release/etalab-ia/albert-api?color=orange&label=version)](https://github.com/etalab-ia/albert-api/releases) 
[![Code Coverage](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/etalab-ia/albert-api/refs/heads/main/.github/badges/coverage.json)](https://github.com/etalab-ia/albert-api)
[![License](https://img.shields.io/github/license/etalab-ia/albert-api?color=red&label=license)](https://github.com/etalab-ia/albert-api/blob/main/LICENSE)
[![French version](https://img.shields.io/badge/🇫🇷-French%20version-blue)](./docs/README_fr.md)

### *✨ Serve all your self-hosted models in one place and manage your users ✨*

[**API Reference**](https://albert.api.etalab.gouv.fr/documentation) | [**Swagger**](https://albert.api.etalab.gouv.fr/swagger)

  </ul>
</div>

## 🔥 Why Albert API?

- 🌐 **OpenAI standards**: based on OpenAI API conventions. Easy to use with OpenAI SDKs, LangChain, LlamaIndex, etc.
* 🚦 **Robust API Gateway:** Load balancing, authentication, and seamless integration with OpenAI, vLLM, HuggingFace TEI.
- 📖 **Open Source**: developed by the French Government, fully open-source forever.
- ⚙️ **Production-ready**: ready to serve your models in production.
* 📚 **Full stack genAI API:** Built-in Retrieval-Augmented Generation (RAG), OCR, audio transcription, and more.
- ✍️ **High code standards**

## 🎯 Key Features

### API Gateway: supported providers

| Provider | Supported endpoints |
| -------- | ------------------- |
| Albert   | Language, Embeddings, Reranking, Transcription |
| OpenAI   | Language, Embeddings, Reranking, Transcription |
| vLLM     | Language |
| HuggingFace TEI | Embeddings, Reranking |

### Advanced AI Capabilities

* **RAG Integration:** Efficiently query vector databases using Elasticsearch or Qdrant.
* **Audio & Vision:** Transcribe audio (Whisper) and perform OCR on PDF documents.
* **Enhanced Security:** Built-in API key authentication.

## 📊 Comparison

| Feature              | Albert API ✅ | LiteLLM   | OpenRouter | OpenAI API |
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

* [**Chat Completions**](https://colab.research.google.com/github/etalab-ia/albert-api/blob/main/docs/tutorials/chat_completions.ipynb)
* [**Multi-Model Access**](https://colab.research.google.com/github/etalab-ia/albert-api/blob/main/docs/tutorials/models.ipynb)
* [**Retrieval-Augmented Generation (RAG)**](https://colab.research.google.com/github/etalab-ia/albert-api/blob/main/docs/tutorials/retrieval_augmented_generation.ipynb)
* [**Knowledge Database Import**](https://colab.research.google.com/github/etalab-ia/albert-api/blob/main/docs/tutorials/import_knowledge_database.ipynb)
* [**Audio Transcriptions**](https://colab.research.google.com/github/etalab-ia/albert-api/blob/main/docs/tutorials/audio_transcriptions.ipynb)
* [**PDF OCR**](https://colab.research.google.com/github/etalab-ia/albert-api/blob/main/docs/tutorials/pdf_ocr.ipynb)

## 🚀 Quickstart

Deploy Albert API quickly with Docker connected to own free model and start using it:

```bash
make quickstart
```
Test the API:

```bash 
curl -X POST "http://localhost:8000/v1/chat/completions" \
-H "Content-Type: application/json" \
-H "Authorization: Bearer changeme" \
-d '{"model": "albert-testbed", "messages": [{"role": "user", "content": "Hello, how are you?"}]}'
```
The default master API key is `changeme`.

### Create a first user

```bash
python scripts/create_first_user.py
```

### Configure your models and add features

With configuration file, you can connect to your own models and add addtionnal services to Albert API. Start by creating a configuration file:

```bash
cp config.example.yml config.yml && export CONFIG_FILE=config.yml
```

Check the [configuration documentation](./docs/configuration.md) to configure your configuration file.

Then, add additional services to Albert API in regard of your configuration file with the following command:

```bash
make add service=<service_name>

# example:
make add service=elasticsearch
```

## 🤝 Contribute

This project exists thanks to all the people who contribute. Albert API thrives on open-source contributions. Join our community!

* [Contribution Guide](./CONTRIBUTING.md)

## Sponsors

<div id="toc">
  <ul align="center" style="list-style: none">
<a href="https://www.numerique.gouv.fr/numerique-etat/dinum/" ><img src="./docs/assets/dinum_logo.png" alt="DINUM logo" width="300" style="margin-right: 40px"></a>
<a href="https://www.centralesupelec.fr"><img src="./docs/assets/centralsupelec_logo.png" alt="CentraleSupélec logo" width="200" style="margin-right: 40px"></a>
  </ul>
</div>