from typing import Optional


from app.helpers import VectorStore
from app.schemas.tools import ToolOutput


class FewShots:
    """
    Fewshots RAG.

    Args:
        embeddings_model (str): OpenAI embeddings model
        collection (str): Collection name. The collection must have question/answer pairs in metadata.
        k (int, optional): Top K per collection. Defaults to 4.
    """

    COLLECTION = "service-public-plus"
    DEFAULT_SYSTEM_PROMPT = "Tu es un générateur de réponse automatique à une expérience utilisateur. Tu parles un français courtois."

    DEFAULT_PROMPT_TEMPLATE = """Vous incarnez un agent chevronné de l'administration française, expert en matière de procédures et réglementations administratives. Votre mission est d'apporter des réponses précises, professionnelles et bienveillantes aux interrogations des usagers, tout en incarnant les valeurs du service public.

Contexte :
Vous avez accès à une base de connaissances exhaustive contenant des exemples de questions fréquemment posées et leurs réponses associées. Utilisez ces informations comme référence pour formuler vos réponses :

{context}

Directives :
1. Adoptez un langage soutenu et élégant, tout en veillant à rester compréhensible pour tous les usagers.
2. Basez-vous sur les exemples fournis pour élaborer des réponses pertinentes et précises.
3. Faites preuve de courtoisie, d'empathie et de pédagogie dans vos interactions, reflétant ainsi l'excellence du service public français.
4. Structurez votre réponse de manière claire et logique, en utilisant si nécessaire des puces ou des numéros pour faciliter la compréhension.
5. En cas d'incertitude sur un point spécifique, indiquez-le clairement et orientez l'usager vers les ressources ou services compétents.
6. Concluez systématiquement votre réponse par une formule de politesse adaptée et proposez votre assistance pour toute question supplémentaire.

Question de l'usager :

{prompt}

Veuillez apporter une réponse circonstanciée à cette question en respectant scrupuleusement les directives énoncées ci-dessus.
"""

    def __init__(self, clients: dict):
        self.clients = clients

    async def get_prompt(
        self,
        embeddings_model: str,
        k: Optional[int] = 4,
        **request,
    ) -> ToolOutput:
        vectorstore = VectorStore(clients=self.clients, user=request["user"])
        collection = vectorstore.get_collection_metadata(collection_names=[self.COLLECTION])[0]
        prompt = request["messages"][-1]["content"]
        results = vectorstore.search(collection_names=[collection.name], prompt=prompt, k=k, model=embeddings_model)

        context = "\n\n\n".join(
            [f"Question: {result.payload.get('question', 'N/A')}\n" f"Réponse: {result.payload.get('answer', 'N/A')}" for result in results]
        )

        prompt = self.DEFAULT_PROMPT_TEMPLATE.format(context=context, prompt=prompt)
        metadata = {"chunks": [result.id for result in results]}

        return ToolOutput(prompt=prompt, metadata=metadata)
