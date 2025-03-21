from fastapi import Depends, FastAPI, Response, Security
from prometheus_fastapi_instrumentator import Instrumentator
from slowapi.middleware import SlowAPIASGIMiddleware

from app.sql.session import get_db
from app.endpoints import endpoints_modules
from app.helpers import MetricsMiddleware, UsagesMiddleware
from app.schemas.security import User
from app.utils.variables import ROUTERS
from app.utils.lifespan import lifespan
from app.utils.security import check_admin_api_key, check_api_key
from app.utils.settings import settings


def create_app(*, db_func=get_db, disabled_middleware=False) -> FastAPI:
    """Create FastAPI application."""
    app = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        description=settings.app_description,
        contact={"url": settings.app_contact_url, "email": settings.app_contact_email},
        licence_info={"name": "MIT License", "identifier": "MIT"},
        lifespan=lifespan,
        docs_url="/swagger",
        redoc_url="/documentation",
    )

    if not disabled_middleware:
        # Prometheus metrics
        app.instrumentator = Instrumentator().instrument(app=app)
        # Middlewares
        app.add_middleware(middleware_class=SlowAPIASGIMiddleware)
        app.add_middleware(middleware_class=UsagesMiddleware, db_func=db_func)
        app.add_middleware(middleware_class=MetricsMiddleware)
        app.instrumentator.expose(app=app, should_gzip=True, tags=["Monitoring"], dependencies=[Depends(dependency=check_admin_api_key)])

    # Add routers
    for endpoint in ROUTERS:
        if endpoint not in settings.disabled_routers:
            app.include_router(router=endpoints_modules[endpoint].router, tags=[endpoint.title()], prefix="/v1")

    # Health check
    @app.get(path="/health", tags=["Monitoring"])
    def health(user: User = Security(dependency=check_api_key)) -> Response:
        """Health check."""
        return Response(status_code=200)

    return app


app = create_app(db_func=get_db, disabled_middleware=settings.disabled_middleware)
