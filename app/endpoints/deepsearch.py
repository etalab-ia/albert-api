import logging
from fastapi import APIRouter, Depends, Request, Security, HTTPException
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional, Union

from app.helpers._accesscontroller import AccessController
from app.helpers._deepsearch import DeepSearchAgent
from app.helpers._websearchmanager import WebSearchManager
from app.schemas.usage import Usage
from app.sql.session import get_db as get_session
from app.utils.context import global_context, request_context
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)
router = APIRouter()

# Schemas spécifiques pour DeepSearch
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
    
    # Vérifier que le DocumentManager et WebSearchManager sont disponibles
    if not global_context.documents:
        raise HTTPException(
            status_code=503, 
            detail="Service de documents non disponible."
        )
    
    if not global_context.documents.web_search:
        raise HTTPException(
            status_code=503, 
            detail="Service WebSearch non disponible. Vérifiez la configuration web_search."
        )
    
    try:
        # Récupérer le modèle spécifié
        model = global_context.models(model=body.model)
        logger.info(f"Using model for DeepSearch: {body.model}")
        
        # Déterminer le WebSearchManager à utiliser
        web_search_manager = global_context.documents.web_search
        
        # Gestion des domaines selon le paramètre limited_domains
        if body.limited_domains is True:
            # Utiliser la configuration par défaut
            logger.info("Using default WebSearchManager with config domains")
        elif body.limited_domains is False:
            # Autoriser tous les domaines (pas de restrictions)
            logger.info("Creating WebSearchManager with no domain restrictions")
            web_search_manager = WebSearchManager(
                web_search=web_search_manager.web_search,
                model=model,
                limited_domains=[],  # Liste vide = pas de restrictions
                user_agent=getattr(web_search_manager, 'user_agent', None)
            )
        elif isinstance(body.limited_domains, list):
            # Utiliser les domaines personnalisés fournis
            logger.info(f"Creating WebSearchManager with custom domains: {len(body.limited_domains)} domains")
            web_search_manager = WebSearchManager(
                web_search=web_search_manager.web_search,
                model=model,
                limited_domains=body.limited_domains,
                user_agent=getattr(web_search_manager, 'user_agent', None)
            )
        
        # Créer l'agent DeepSearch avec le WebSearchManager approprié
        deepsearch_agent = DeepSearchAgent(
            model=model,
            web_search_manager=web_search_manager
        )
        
        logger.info(f"Starting DeepSearch with model: {body.model} for prompt: {body.prompt[:100]}...")
        
        # Effectuer la recherche approfondie
        final_response, sources, metadata = await deepsearch_agent.deep_search(
            prompt=body.prompt,
            session=session,
            k=body.k,
            iteration_limit=body.iteration_limit,
            num_queries=body.num_queries,
            lang=body.lang
        )
        
        # Ajouter le modèle utilisé dans les métadonnées
        metadata["model_used"] = body.model
        
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
        
        logger.info(f"DeepSearch completed with {body.model}: {len(sources)} sources, {metadata['elapsed_time']:.2f}s, {usage.total_tokens} tokens")
        return JSONResponse(content=result.model_dump(), status_code=200)
        
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
    
    # Vérifier le DocumentManager
    if global_context.documents:
        status["document_manager_initialized"] = True
        
        # Vérifier la configuration WebSearchManager
        if global_context.documents.web_search:
            status["web_search_manager_configured"] = True
            
            # Récupérer les informations de configuration
            web_search_manager = global_context.documents.web_search
            if hasattr(web_search_manager, 'limited_domains'):
                status["default_limited_domains"] = web_search_manager.limited_domains
            if hasattr(web_search_manager, 'user_agent'):
                status["web_search_user_agent"] = web_search_manager.user_agent
    
    # Lister tous les modèles disponibles
    if global_context.models:
        try:
            available_models = []
            for router in global_context.models.routers:
                available_models.append(router.id)
            status["available_models"] = available_models
        except Exception as e:
            logger.warning(f"Could not retrieve available models: {e}")
    
    # Déterminer la disponibilité générale
    if status["document_manager_initialized"] and status["web_search_manager_configured"] and status["available_models"]:
        status["available"] = True
        domains_count = len(status["default_limited_domains"]) if status["default_limited_domains"] else 0
        status["message"] = f"DeepSearch disponible. Modèles: {len(status['available_models'])}, Domaines config: {domains_count}. Utilisez limited_domains=true/false/[liste]"
    else:
        if not status["document_manager_initialized"]:
            status["message"] = "DocumentManager non initialisé"
        elif not status["web_search_manager_configured"]:
            status["message"] = "WebSearchManager non configuré - vérifiez la configuration web_search"
        elif not status["available_models"]:
            status["message"] = "Aucun modèle disponible"
        else:
            status["message"] = "Service non disponible"
    
    return JSONResponse(content=status, status_code=200)