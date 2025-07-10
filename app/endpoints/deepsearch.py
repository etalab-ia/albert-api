
import logging
from fastapi import APIRouter, Depends, Request, Security, HTTPException
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List

from app.helpers._accesscontroller import AccessController
from app.schemas.usage import Usage
from app.sql.session import get_db as get_session
from app.utils.context import global_context, request_context
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)
router = APIRouter()

# Schemas spécifiques pour DeepSearch
class DeepSearchRequest(BaseModel):
    prompt: str = Field(description="Question ou requête pour la recherche approfondie")
    k: int = Field(default=5, ge=1, le=10, description="Nombre de résultats par requête de recherche")
    iteration_limit: int = Field(default=2, ge=1, le=5, description="Nombre maximum d'itérations de recherche")
    num_queries: int = Field(default=2, ge=1, le=5, description="Nombre de requêtes à générer par itération")
    lang: str = Field(default='fr', description="Langue pour la recherche (fr ou en)")


class DeepSearchMetadata(BaseModel):
    total_input_tokens: int = Field(description="Total des tokens d'entrée utilisés")
    total_output_tokens: int = Field(description="Total des tokens de sortie utilisés")
    elapsed_time: float = Field(description="Temps total écoulé en secondes")
    iterations: int = Field(description="Nombre d'itérations effectuées")
    total_queries: int = Field(description="Nombre total de requêtes générées")
    sources_found: int = Field(description="Nombre de sources trouvées")


class DeepSearchResponse(BaseModel):
    object: str = "deepsearch_result"
    prompt: str = Field(description="Requête originale")
    response: str = Field(description="Réponse générée basée sur les sources trouvées")
    sources: List[str] = Field(description="Liste des URLs sources")
    metadata: DeepSearchMetadata = Field(description="Métadonnées sur le processus de recherche")
    usage: Usage = Field(description="Informations d'usage pour la requête")


@router.post(
    path="/deepsearch", 
    dependencies=[Security(dependency=AccessController())], 
    status_code=200, 
    response_model=DeepSearchResponse
)
async def deepsearch(
    request: Request, 
    body: DeepSearchRequest, 
    session: AsyncSession = Depends(get_session)
) -> JSONResponse:
    """
    Effectue une recherche approfondie sur le web et génère une réponse complète.
    
    Cette endpoint :
    1. Génère plusieurs requêtes de recherche basées sur la question utilisateur
    2. Recherche sur le web via l'API Brave Search
    3. Évalue et extrait le contenu pertinent des pages trouvées
    4. Affine itérativement les requêtes selon le contenu trouvé
    5. Génère une réponse complète basée sur toutes les informations rassemblées
    
    Nécessite une clé API Brave Search configurée.
    """
    
    # Vérifier si l'agent DeepSearch est disponible
    if not hasattr(global_context, 'deepsearch_agent') or not global_context.deepsearch_agent:
        raise HTTPException(
            status_code=503, 
            detail="Service DeepSearch non disponible. Vérifiez la configuration BRAVE_SEARCH_API_KEY."
        )
    
    try:
        logger.info(f"Starting DeepSearch for prompt: {body.prompt[:100]}...")
        
        # Effectuer la recherche approfondie
        final_response, sources, metadata = await global_context.deepsearch_agent.deep_search(
            prompt=body.prompt,
            session=session,
            k=body.k,
            iteration_limit=body.iteration_limit,
            num_queries=body.num_queries,
            lang=body.lang
        )
        
        # Créer la réponse
        deep_search_metadata = DeepSearchMetadata(**metadata)
        usage = Usage(
            prompt_tokens=metadata["total_input_tokens"],
            completion_tokens=metadata["total_output_tokens"],
            total_tokens=metadata["total_input_tokens"] + metadata["total_output_tokens"]
        )
        
        # Mettre à jour l'usage dans le contexte de la requête
        ctx = request_context.get()
        if ctx and ctx.usage:
            ctx.usage.prompt_tokens += usage.prompt_tokens
            ctx.usage.completion_tokens += usage.completion_tokens
            ctx.usage.total_tokens += usage.total_tokens
        
        result = DeepSearchResponse(
            prompt=body.prompt,
            response=final_response,
            sources=sources,
            metadata=deep_search_metadata,
            usage=usage
        )
        
        logger.info(f"DeepSearch completed: {len(sources)} sources, {metadata['elapsed_time']:.2f}s, {usage.total_tokens} tokens")
        return JSONResponse(content=result.model_dump(), status_code=200)
        
    except Exception as e:
        logger.error(f"DeepSearch failed for prompt '{body.prompt}': {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Échec de la recherche approfondie : {str(e)}")

@router.get(
    path="/deepsearch/status",
    dependencies=[Security(dependency=AccessController())],
    status_code=200
)
async def deepsearch_status(request: Request) -> JSONResponse:
    """
    Vérifie le statut de disponibilité du service DeepSearch.
    """
    import os
    
    status = {
        "available": False,
        "deepsearch_agent_initialized": False,
        "web_search_manager_configured": False,
        "model_configured": False,
        "model_id": None,
        "web_search_domains": None,
        "message": ""
    }
    
    # Vérifier la configuration de base
    if hasattr(global_context, 'documents') and global_context.documents and hasattr(global_context.documents, 'web_search'):
        web_search_manager = global_context.documents.web_search
        if web_search_manager:
            status["web_search_manager_configured"] = True
            status["web_search_domains"] = web_search_manager.limited_domains
    
    # Vérifier l'agent
    if hasattr(global_context, 'deepsearch_agent') and global_context.deepsearch_agent:
        status["deepsearch_agent_initialized"] = True
        status["model_configured"] = True
        status["model_id"] = global_context.deepsearch_agent.model.id
        status["available"] = True
        status["message"] = f"DeepSearch disponible avec WebSearchManager et modèle {status['model_id']}"
    else:
        if not status["web_search_manager_configured"]:
            status["message"] = "WebSearchManager non configuré - vérifiez la configuration web_search"
        elif not hasattr(global_context, 'models') or not global_context.models:
            status["message"] = "Gestionnaire de modèles non initialisé"
        else:
            status["message"] = "Agent DeepSearch non initialisé"
    
    return JSONResponse(content=status, status_code=200)