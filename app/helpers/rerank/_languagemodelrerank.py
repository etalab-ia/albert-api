import re
from typing import List

from app.schemas.rerank import Rerank


class LanguageModelRerank:
    PROMPT_LLM_BASED = """Voilà un texte : {text}

En se basant uniquement sur ce texte, réponds 1 si ce texte peut donner des éléments de réponse à la question suivante ou 0 si aucun élément de réponse n'est présent dans le texte.

Voilà la question: {prompt}

Le texte n'a pas besoin de répondre parfaitement à la question, juste d'apporter des éléments de réponses et/ou de parler du même thème. Réponds uniquement 0 ou 1.
"""

    def __init__(self, client=None) -> None:
        self.client = client

    async def create(self, prompt: str, input: list, model: str) -> List[Rerank]:
        data = list()
        for index, text in enumerate(input):
            content = self.PROMPT_LLM_BASED.format(prompt=prompt, text=text)

            response = await self.client.chat.completions.create(
                messages=[{"role": "user", "content": content}], model=model, temperature=0.1, max_tokens=3, stream=False, n=1
            )
            result = response.choices[0].message.content
            match = re.search(r"[0-1]", result)
            result = int(match.group(0)) if match else 0
            data.append(Rerank(score=result, index=index))

        return data
