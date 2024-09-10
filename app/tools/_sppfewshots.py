from typing import List, Optional

from fastapi import HTTPException
from qdrant_client.http import models as rest

from app.utils.data import (
    search_multiple_collections,
    get_collection_id,
    get_collection_metadata,
)
from app.schemas.tools import ToolOutput


class SPPFewShots:
    """
    Service Public Plus Fewshots RAG.

    Args:
        embeddings_model (str): OpenAI embeddings model
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
        collection_id = get_collection_id(
            vectorstore=self.clients["vectors"], user=request["user"], collection=self.COLLECTION
        )
        collection_metadata = get_collection_metadata(
            vectorstore=self.clients["vectors"], user=request["user"], collection=self.COLLECTION
        )
        if collection_metadata.model != embeddings_model:
            raise HTTPException(
                status_code=400,
                detail=f"{collection_metadata.id} collection is set for {collection_metadata.model} model.",
            )
        prompt = request["messages"][-1]["content"]
        response = self.clients["models"][embeddings_model].embeddings.create(
            input=[prompt], model=embeddings_model
        )
        vector = response.data[0].embedding

        results = self.clients["vectors"].search(
            collection_name=collection_id, query_vector=vector, limit=k
        )

        context = "\n\n\n".join([
            f"Question: {result.payload.get('description', 'N/A')}\n"
            f"Réponse: {result.payload.get('reponse', 'N/A')}"
            for result in results
        ])

        prompt = self.DEFAULT_PROMPT_TEMPLATE.format(context=context, prompt=prompt)
        metadata = {"chunks": [result.id for result in results]}

        return ToolOutput(prompt=prompt, metadata=metadata)
