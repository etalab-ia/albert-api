import logging

from fastapi import APIRouter, Depends, FastAPI, Request, Response, Security
from fastapi.dependencies.utils import get_dependant
from prometheus_fastapi_instrumentator import Instrumentator
import sentry_sdk
from starlette.middleware.sessions import SessionMiddleware


from app.endpoints import oauth2
from app.schemas.auth import PermissionType
from app.schemas.core.context import RequestContext
from app.schemas.usage import Usage
from app.utils.context import generate_request_id, request_context
from app.sql.session import set_get_db_func
from app.utils.hooks_decorator import hooks
from app.utils.variables import (
    ROUTER__USAGE,
    ROUTER__AGENTS,
    ROUTER__AUDIO,
    ROUTER__AUTH,
    ROUTER__CHAT,
    ROUTER__CHUNKS,
    ROUTER__COLLECTIONS,
    ROUTER__COMPLETIONS,
    ROUTER__DOCUMENTS,
    ROUTER__EMBEDDINGS,
    ROUTER__FILES,
    ROUTER__MODELS,
    ROUTER__MONITORING,
    ROUTER__OCR,
    ROUTER__PARSE,
    ROUTER__RERANK,
    ROUTER__SEARCH,
    ROUTER__USERS,
    ROUTER__OAUTH2,
)

logger = logging.getLogger(__name__)


def create_app(db_func=None, *args, **kwargs) -> FastAPI:
    """Create FastAPI application."""
    if db_func is not None:
        set_get_db_func(db_func)
    from app.utils.lifespan import lifespan

    from app.utils.configuration import configuration

    if configuration.dependencies.sentry:
        logger.info("Initializing Sentry SDK.")
        sentry_sdk.init(**configuration.dependencies.sentry.model_dump())

    app = FastAPI(
        title=configuration.settings.swagger_title,
        summary=configuration.settings.swagger_summary,
        version=configuration.settings.swagger_version,
        description=configuration.settings.swagger_description,
        terms_of_service=configuration.settings.swagger_terms_of_service,
        contact=configuration.settings.swagger_contact,
        licence_info=configuration.settings.swagger_license_info,
        openapi_tags=configuration.settings.swagger_openapi_tags,
        docs_url=configuration.settings.swagger_docs_url,
        redoc_url=configuration.settings.swagger_redoc_url,
        lifespan=lifespan,
    )
    app.add_middleware(SessionMiddleware, secret_key=configuration.settings.session_secret_key)

    # Set up database dependency
    # If no db_func provided, the depends module will fall back to default
    from app.endpoints import (
        agents,
        audio,
        chat,
        chunks,
        collections,
        completions,
        documents,
        embeddings,
        files,
        models,
        ocr,
        parse,
        rerank,
        roles,
        search,
        usage,
        users,
    )
    from app.helpers._accesscontroller import AccessController

    def add_hooks(router: APIRouter) -> None:
        for route in router.routes:
            route.endpoint = hooks(route.endpoint)
            route.dependant = get_dependant(path=route.path_format, call=route.endpoint)

    @app.middleware("http")
    async def set_request_context(request: Request, call_next):
        """Middleware to set request context."""
        request_context.set(
            RequestContext(
                id=generate_request_id(),
                method=request.method,
                endpoint=request.url.path,
                client=request.client.host,
                usage=Usage(),
            )
        )

        return await call_next(request)

    # Routers
    if ROUTER__AGENTS not in configuration.settings.disabled_routers:
        add_hooks(router=agents.router)
        app.include_router(router=agents.router, tags=[ROUTER__AGENTS.title()], prefix="/v1")

    if ROUTER__AUDIO not in configuration.settings.disabled_routers:
        add_hooks(router=audio.router)
        app.include_router(router=audio.router, tags=[ROUTER__AUDIO.title()], prefix="/v1")

    if ROUTER__AUTH not in configuration.settings.disabled_routers:
        add_hooks(router=roles.router)
        app.include_router(router=roles.router, tags=[ROUTER__AUTH.title()])

    if ROUTER__CHAT not in configuration.settings.disabled_routers:
        add_hooks(router=chat.router)
        app.include_router(router=chat.router, tags=[ROUTER__CHAT.title()], prefix="/v1")

    if ROUTER__CHUNKS not in configuration.settings.disabled_routers:
        add_hooks(router=chunks.router)
        app.include_router(router=chunks.router, tags=[ROUTER__CHUNKS.title()], prefix="/v1")

    if ROUTER__COLLECTIONS not in configuration.settings.disabled_routers:
        add_hooks(router=collections.router)
        app.include_router(router=collections.router, tags=[ROUTER__COLLECTIONS.title()], prefix="/v1")

    if ROUTER__DOCUMENTS not in configuration.settings.disabled_routers:
        add_hooks(router=documents.router)
        app.include_router(router=documents.router, tags=[ROUTER__DOCUMENTS.title()], prefix="/v1")

    if ROUTER__EMBEDDINGS not in configuration.settings.disabled_routers:
        add_hooks(router=embeddings.router)
        app.include_router(router=embeddings.router, tags=[ROUTER__EMBEDDINGS.title()], prefix="/v1")

    if ROUTER__MODELS not in configuration.settings.disabled_routers:
        add_hooks(router=models.router)
        app.include_router(router=models.router, tags=[ROUTER__MODELS.title()], prefix="/v1")

    if ROUTER__MONITORING not in configuration.settings.disabled_routers:
        if configuration.settings.monitoring_prometheus_enabled:
            app.instrumentator = Instrumentator().instrument(app=app)
            app.instrumentator.expose(app=app, should_gzip=True, tags=[ROUTER__MONITORING.title()], dependencies=[Depends(dependency=AccessController(permissions=[PermissionType.READ_METRIC]))], include_in_schema=configuration.settings.log_level == "DEBUG")  # fmt: off

        @app.get(path="/health", tags=[ROUTER__MONITORING.title()], include_in_schema=configuration.settings.log_level == "DEBUG", dependencies=[Security(dependency=AccessController())])  # fmt: off
        def health() -> Response:
            return Response(status_code=200)

    if ROUTER__OCR not in configuration.settings.disabled_routers:
        add_hooks(router=ocr.router)
        app.include_router(router=ocr.router, tags=[ROUTER__OCR.upper()], prefix="/v1")

    if ROUTER__PARSE not in configuration.settings.disabled_routers:
        add_hooks(router=parse.router)
        app.include_router(router=parse.router, tags=[ROUTER__PARSE.title()], prefix="/v1")

    if ROUTER__RERANK not in configuration.settings.disabled_routers:
        add_hooks(router=rerank.router)
        app.include_router(router=rerank.router, tags=[ROUTER__RERANK.title()], prefix="/v1")

    if ROUTER__SEARCH not in configuration.settings.disabled_routers:
        add_hooks(router=search.router)
        app.include_router(router=search.router, tags=[ROUTER__SEARCH.title()], prefix="/v1")

    if ROUTER__USAGE not in configuration.settings.disabled_routers:
        add_hooks(router=usage.router)
        app.include_router(router=usage.router, tags=[ROUTER__USAGE.title()], prefix="/v1")

    if ROUTER__USERS not in configuration.settings.disabled_routers:
        add_hooks(router=users.router)
        app.include_router(router=users.router, tags=[ROUTER__USERS.title()])

    # DEPRECATED LEGACY ENDPOINTS
    if ROUTER__COMPLETIONS not in configuration.settings.disabled_routers:
        add_hooks(router=completions.router)
        app.include_router(router=completions.router, tags=["Legacy"], prefix="/v1")

    if ROUTER__FILES not in configuration.settings.disabled_routers:
        # hooks does not work with files endpoint (request is overwritten by the file upload)
        app.include_router(router=files.router, tags=["Legacy"], prefix="/v1")

    if configuration.dependencies.oauth2 and ROUTER__OAUTH2 not in configuration.settings.disabled_routers:
        add_hooks(router=oauth2.router)
        app.include_router(router=oauth2.router, tags=[ROUTER__OAUTH2.title()], prefix="/v1")

    return app
