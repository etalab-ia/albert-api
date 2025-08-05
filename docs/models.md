# Models

OpenGateLLM permet de configurer 4 types de modèles :
- text-generation : modèle de language
- text-embeddings-inference : modèle d'embeddings
- automatic-speech-recognition : modèle de transcription audio.
- text-classification : modèle de reranking

Pour configurer la connexion à ces modèles, voir la documentation [deployment](./deployment.md).

## text-generation

Pour les modèles de language, vous pouvez utiliser n'importe quel API compatible avec le format [OpenAI](https://platform.openai.com/docs/api-reference/chat/create), c'est-à-dire disposant d'un endpoint `/v1/chat/completions`.

Si vous souhaitez déployer un modèle de language, vous recommandons d'utiliser [vLLM](https://github.com/vllm-project/vllm). Exemple de modèle de language : [guillaumetell-7b](https://huggingface.co/AgentPublic/guillaumetell-7b).

**⚠️ Le déploiement de l'API est pas conditionné à la fourniture d'un modèle de language.**

## text-embeddings-inference

Pour les modèles d'embeddings, vous pouvez utiliser n'importe quel API compatible avec le format [OpenAI](https://platform.openai.com/docs/api-reference/embeddings), c'est-à-dire disposant d'un endpoint `/v1/embeddings`.

Si vous souhaitez déployer un modèle d'embeddings, vous recommandons d'utiliser [HuggingFace Text Embeddings Inference](https://github.com/huggingface/text-embeddings-inference). Exemple de modèle d'embeddings : [multilingual-e5-large](https://huggingface.co/intfloat/multilingual-e5-large).

**⚠️ Le déploiement de l'API est conditionné à la fourniture d'un modèle d'embeddings.**

## automatic-speech-recognition

Pour les modèles de transcription audio, vous pouvez utiliser n'importe quel API compatible avec le format [OpenAI](https://platform.openai.com/docs/api-reference/audio/create-transcription), c'est-à-dire disposant d'un endpoint `/v1/audio/transcriptions`.

Si vous souhaitez déployer un modèle de transcription audio, vous recommandons d'utiliser [Whisper OpenAI API](https://github.com/etalab-ia/whisper-openai-api). Exemple de modèle de transcription audio : [whisper-large-v3-turbo](https://huggingface.co/openai/whisper-large-v3-turbo).

Le déploiement de l'API n'est pas conditionné à la fourniture d'un modèle de transcription audio.

## text-classification

Pour les modèles de reranking, vous devez une API compatible avec le format proposé par l'API [HuggingFace Text Embeddings Inference](https://huggingface.github.io/text-embeddings-inference/), c'est-à-dire disposant d'un endpoint `/rerank`.

Si vous souhaitez déployer un modèle de reranking, vous recommandons d'utiliser [HuggingFace Text Embeddings Inference](https://github.com/huggingface/text-embeddings-inference). Exemple de modèle de reranking : [bge-reranker-v2-m3](https://huggingface.co/BAAI/bge-reranker-v2-m3).

Le déploiement de l'API n'est pas conditionné à la fourniture d'un modèle de reranking.
