import logging

from fastapi import APIRouter, Depends, HTTPException, Request, Security
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.helpers._accesscontroller import AccessController
from app.helpers._deepsearch import DeepSearchAgent
from app.helpers._websearchmanager import WebSearchManager
from app.schemas.deepsearch import DeepSearchMetadata, DeepSearchRequest, DeepSearchResponse
from app.schemas.usage import Usage
from app.sql.session import get_db as get_session
from app.utils.context import global_context, request_context

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post(path="/deepsearch", dependencies=[Security(dependency=AccessController())], status_code=200, response_model=DeepSearchResponse)
async def deepsearch(request: Request, body: DeepSearchRequest, session: AsyncSession = Depends(get_session)) -> JSONResponse:
    """
    Perform an in-depth web search and generate a comprehensive answer.

    This endpoint:
    1. Generates multiple search queries based on the user's question
    2. Searches the web using the WebSearchManager API
    3. Evaluates and extracts relevant content from found pages
    4. Iteratively refines queries based on the content found
    5. Generates a comprehensive response based on all collected information

    The model must be specified via the required 'model' parameter.

    Domain handling with 'limited_domains':
    - True (default): use domains configured in config.yml
    - False: allow all domains (no restrictions)
    - [list]: only use the domains specified in the list
    """

    try:
        # Preliminary checks
        if not global_context.model_registry:
            raise HTTPException(status_code=500, detail="model_registry not initialized")

        if not global_context.document_manager:
            raise HTTPException(status_code=500, detail="document_manager not initialized")

        if not global_context.document_manager.web_search_manager:
            raise HTTPException(status_code=500, detail="WebSearchManager not configured")

        try:
            model = global_context.model_registry(model=body.model)
            logger.info(f"Using model for DeepSearch: {body.model}")
        except Exception as e:
            logger.error(f"Failed to get model '{body.model}': {e}")
            raise HTTPException(status_code=400, detail=f"Model '{body.model}' not found: {str(e)}")

        web_search_manager = global_context.document_manager.web_search_manager

        if body.limited_domains is False:
            logger.info("Creating WebSearchManager with no domain restrictions")
            web_search_manager = WebSearchManager(
                web_search_engine=web_search_manager.web_search_engine,
                query_model=model,
                limited_domains=[],
                user_agent=getattr(web_search_manager, "user_agent", None),
            )
        elif isinstance(body.limited_domains, list):
            logger.info(f"Creating WebSearchManager with custom domains: {len(body.limited_domains)} domains")
            web_search_manager = WebSearchManager(
                web_search_engine=web_search_manager.web_search_engine,
                query_model=model,
                limited_domains=body.limited_domains,
                user_agent=getattr(web_search_manager, "user_agent", None),
            )

        deepsearch_agent = DeepSearchAgent(model=model, web_search_manager=web_search_manager)

        logger.info(f"Starting DeepSearch with model: {body.model} for prompt: {body.prompt[:100]}...")

        final_response, sources, metadata = await deepsearch_agent.deep_search(
            prompt=body.prompt, session=session, k=body.k, iteration_limit=body.iteration_limit, num_queries=body.num_queries, lang=body.lang
        )

        metadata["model_used"] = body.model

        deep_search_metadata = DeepSearchMetadata(**metadata)
        usage = Usage(
            prompt_tokens=metadata["total_input_tokens"],
            completion_tokens=metadata["total_output_tokens"],
            total_tokens=metadata["total_input_tokens"] + metadata["total_output_tokens"],
        )

        ctx = request_context.get()
        if ctx and ctx.usage:
            ctx.usage.prompt_tokens += usage.prompt_tokens
            ctx.usage.completion_tokens += usage.completion_tokens
            ctx.usage.total_tokens += usage.total_tokens

        result = DeepSearchResponse(prompt=body.prompt, response=final_response, sources=sources, metadata=deep_search_metadata, usage=usage)

        logger.info(f"DeepSearch completed with {body.model}: {len(sources)} sources, {metadata["elapsed_time"]:.2f}s, {usage.total_tokens} tokens")
        return JSONResponse(content=result.model_dump(), status_code=200)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"DeepSearch failed for prompt '{body.prompt}' with model '{body.model}': {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Deep search failed: {str(e)}")
