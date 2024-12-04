import re


from app.helpers._modelclients import ModelClients


class RerankClient:
    PROMPT_LLM_BASED = """Voila un texte : {doc}\n 
        En se basant uniquement sur ce texte, réponds 1 si ce texte peut donner des éléments de réponse à la question suivante ou 0 si aucun élément de réponse n'est présent dans le texte. Voila la question: {prompt}
        Le texte n'a pas besoin de répondre parfaitement à la question, juste d'apporter des éléments de réponses et/ou de parler du même thème. Réponds uniquement 0 ou 1."""
    PROMPT_CHOICER = """"""

    def __init__(
        self,
        model_clients: ModelClients,
        # search_client: SearchClient,
    ):
        self.model_clients = model_clients
        # self.search_client = search_client

    def get_rank(self, prompt: str, inputs: list, model: str, rerank_type: str) -> str:
        if rerank_type == "classic_rerank":
            # TODO: Add classic reranker
            return []

        elif rerank_type == "llm_rerank":
            prompts = []
            for doc in inputs:
                prompt_ = self.PROMPT_LLM_BASED.format(prompt=prompt, doc=doc)
                prompts.append(prompt_)

            results = []
            for prompt in prompts:
                response = self.model_clients[model].chat.completions.create(
                    messages=[{"role": "user", "content": prompt}],
                    model=self.model_clients.DEFAULT_INTERNET_LANGUAGE_MODEL_ID,
                    temperature=0.1,
                    max_tokens=3,
                    stream=False,
                )
                result = response.choices[0].message.content

                match = re.search(r"[0-1]", result)
                result = int(match.group(0)) if match else 0
                results.append(result)
            return results

        elif rerank_type == "choicer":
            return ["Ici la voix"]
