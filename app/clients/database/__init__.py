from app.schemas.core.settings import DatabaseType
from ._elasticsearchclient import ElasticsearchClient
from ._qdrantclient import QdrantClient

from app.utils.context import global_context
from app.schemas.core.settings import Settings

__all__ = ["ElasticsearchClient", "QdrantClient"]


def get_vector_store(settings: Settings):  # TODO: return an abstract interface for the "vector_store"
    if settings.databases.vector_store.type == DatabaseType.QDRANT:
        vector_store = QdrantClient(**settings.databases.vector_store.args)
    elif settings.databases.vector_store.type == DatabaseType.ELASTICSEARCH:
        vector_store = ElasticsearchClient(**settings.databases.vector_store.args)
    else:
        vector_store = None

    if vector_store and global_context.models:
        vector_store.model = global_context.models(model=settings.databases.vector_store.model)

    return vector_store
