import logging
from fastapi import APIRouter, Depends, Request, Security, HTTPException
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional, Union

from app.helpers._accesscontroller import AccessController
from app.helpers._deepwebsearch import DeepSearchAgent
from app.helpers._websearchmanager import WebSearchManager
from app.schemas.usage import Usage
from app.sql.session import get_db as get_session
from app.utils.context import global_context, request_context
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)
router = APIRouter()

class DeepSearchRequest(BaseModel):
    prompt: str = Field(description="Question ou requête pour la recherche approfondie")
    model: str = Field(description="ID du modèle à utiliser pour DeepSearch")
    k: int = Field(default=5, ge=1, le=10, description="Nombre de résultats par requête de recherche")
    iteration_limit: int = Field(default=2, ge=1, le=5, description="Nombre maximum d'itérations de recherche")
    num_queries: int = Field(default=2, ge=1, le=5, description="Nombre de requêtes à générer par itération")
    lang: str = Field(default='fr', description="Langue pour la recherche (fr ou en)")
    limited_domains: Union[bool, List[str]] = Field(
        default=True, 
        description="Gestion des domaines autorisés : True = utilise config par défaut, False = tous domaines autorisés, [liste] = domaines personnalisés"
    )


class DeepSearchMetadata(BaseModel):
    total_input_tokens: int = Field(description="Total des tokens d'entrée utilisés")
    total_output_tokens: int = Field(description="Total des tokens de sortie utilisés")
    elapsed_time: float = Field(description="Temps total écoulé en secondes")
    iterations: int = Field(description="Nombre d'itérations effectuées")
    total_queries: int = Field(description="Nombre total de requêtes générées")
    sources_found: int = Field(description="Nombre de sources trouvées")
    model_used: str = Field(description="Modèle utilisé pour la recherche")


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
    2. Recherche sur le web via l'API WebSearchManager
    3. Évalue et extrait le contenu pertinent des pages trouvées
    4. Affine itérativement les requêtes selon le contenu trouvé
    5. Génère une réponse complète basée sur toutes les informations rassemblées
    
    Le modèle doit être spécifié via le paramètre 'model' obligatoire.
    
    Gestion des domaines avec 'limited_domains' :
    - True (défaut) : utilise les domaines configurés dans config.yml
    - False : autorise tous les domaines (pas de restrictions)
    - [liste] : utilise uniquement les domaines spécifiés dans la liste
    """

    try:
        # Vérifications préliminaires
        if not global_context.model_registry:
            raise HTTPException(status_code=500, detail="model_registry non initialisé")
        
        if not global_context.document_manager:
            raise HTTPException(status_code=500, detail="document_manager non initialisé")
        
        if not global_context.document_manager.web_search_manager:
            raise HTTPException(status_code=500, detail="WebSearchManager non configuré")
        
        try:
            model = global_context.model_registry(model=body.model)
            logger.info(f"Using model for DeepSearch: {body.model}")
        except Exception as e:
            logger.error(f"Failed to get model '{body.model}': {e}")
            raise HTTPException(status_code=400, detail=f"Modèle '{body.model}' non trouvé: {str(e)}")
        
        web_search_manager = global_context.document_manager.web_search_manager
        
        if body.limited_domains is False:
            logger.info("Creating WebSearchManager with no domain restrictions")
            web_search_manager = WebSearchManager(
                web_search_engine=web_search_manager.web_search_engine,
                query_model=model,
                limited_domains=[],  # Liste vide = pas de restrictions
                user_agent=getattr(web_search_manager, 'user_agent', None)
            )
        elif isinstance(body.limited_domains, list):
            logger.info(f"Creating WebSearchManager with custom domains: {len(body.limited_domains)} domains")
            web_search_manager = WebSearchManager(
                web_search_engine=web_search_manager.web_search_engine,
                query_model=model,
                limited_domains=body.limited_domains,
                user_agent=getattr(web_search_manager, 'user_agent', None)
            )
        
        deepsearch_agent = DeepSearchAgent(
            model=model,
            web_search_manager=web_search_manager
        )
        
        logger.info(f"Starting DeepSearch with model: {body.model} for prompt: {body.prompt[:100]}...")
        
        final_response, sources, metadata = await deepsearch_agent.deep_search(
            prompt=body.prompt,
            session=session,
            k=body.k,
            iteration_limit=body.iteration_limit,
            num_queries=body.num_queries,
            lang=body.lang
        )
        
        metadata["model_used"] = body.model
        
        deep_search_metadata = DeepSearchMetadata(**metadata)
        usage = Usage(
            prompt_tokens=metadata["total_input_tokens"],
            completion_tokens=metadata["total_output_tokens"],
            total_tokens=metadata["total_input_tokens"] + metadata["total_output_tokens"]
        )
        
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
        
        logger.info(f"DeepSearch completed with {body.model}: {len(sources)} sources, {metadata['elapsed_time']:.2f}s, {usage.total_tokens} tokens")
        return JSONResponse(content=result.model_dump(), status_code=200)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"DeepSearch failed for prompt '{body.prompt}' with model '{body.model}': {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Échec de la recherche approfondie : {str(e)}")


@router.get(
    path="/deepsearch/status",
    dependencies=[Security(dependency=AccessController())],
    status_code=200
)
async def deepsearch_status(request: Request) -> JSONResponse:
    """
    Vérifie le statut de disponibilité du service DeepSearch.
    
    Retourne les informations de configuration incluant :
    - Disponibilité du service
    - Modèles disponibles
    - Domaines configurés par défaut
    - Exemples d'usage pour limited_domains
    """
    status = {
        "available": False,
        "model_registry_initialized": False,
        "document_manager_initialized": False,
        "web_search_manager_configured": False,
        "available_models": [],
        "default_limited_domains": None,
        "web_search_user_agent": None,
        "usage_examples": {
            "config_domains": {"limited_domains": True},
            "all_domains": {"limited_domains": False},
            "custom_domains": {"limited_domains": ["wikipedia.org", "stackoverflow.com"]}
        },
        "message": ""
    }
    
    if global_context.model_registry:
        status["model_registry_initialized"] = True
        
        try:
            if hasattr(global_context.model_registry, 'routers'):
                status["available_models"] = [router.id for router in global_context.model_registry.routers if hasattr(router, 'id')]
        except Exception as e:
            logger.warning(f"Could not retrieve available models: {e}")
    
    if global_context.document_manager:
        status["document_manager_initialized"] = True
        
        if global_context.document_manager.web_search_manager:
            status["web_search_manager_configured"] = True
            
            web_search_manager = global_context.document_manager.web_search_manager
            if hasattr(web_search_manager, 'limited_domains'):
                status["default_limited_domains"] = web_search_manager.limited_domains
            if hasattr(web_search_manager, 'user_agent'):
                status["web_search_user_agent"] = web_search_manager.user_agent
    
    if (status["model_registry_initialized"] and 
        status["document_manager_initialized"] and 
        status["web_search_manager_configured"] and 
        status["available_models"]):
        
        status["available"] = True
        domains_count = len(status["default_limited_domains"]) if status["default_limited_domains"] else 0
        status["message"] = f"DeepSearch disponible. Modèles: {len(status['available_models'])}, Domaines config: {domains_count}. Utilisez limited_domains=true/false/[liste]"
    else:
        if not status["model_registry_initialized"]:
            status["message"] = "model_registry non initialisé dans global_context"
        elif not status["document_manager_initialized"]:
            status["message"] = "document_manager non initialisé dans global_context"
        elif not status["web_search_manager_configured"]:
            status["message"] = "WebSearchManager non configuré dans global_context.document_manager"
        elif not status["available_models"]:
            status["message"] = "Aucun modèle disponible dans model_registry"
        else:
            status["message"] = "Service non disponible"
    
    return JSONResponse(content=status, status_code=200)