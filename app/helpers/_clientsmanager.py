from redis.asyncio import Redis as CacheManager
from redis.asyncio.connection import ConnectionPool

from app.clients import AuthenticationClient, ModelClients
from app.clients.internet import DuckDuckGoInternetClient, BraveInternetClient
from app.clients.search import ElasticSearchClient, QdrantSearchClient
from app.schemas.settings import Settings
from app.utils.variables import INTERNET_CLIENT_BRAVE_TYPE, INTERNET_CLIENT_DUCKDUCKGO_TYPE, SEARCH_CLIENT_ELASTIC_TYPE, SEARCH_CLIENT_QDRANT_TYPE


class ClientsManager:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    def set(self):
        self.models = ModelClients(settings=self.settings)

        self.cache = CacheManager(connection_pool=ConnectionPool(**self.settings.cache.args))

        if self.settings.search.type == SEARCH_CLIENT_ELASTIC_TYPE:
            self.search = ElasticSearchClient(models=self.models, **self.settings.search.args)
        elif self.settings.search.type == SEARCH_CLIENT_QDRANT_TYPE:
            self.search = QdrantSearchClient(models=self.models, **self.settings.search.args)

        if self.settings.internet.type == INTERNET_CLIENT_DUCKDUCKGO_TYPE:
            self.internet = DuckDuckGoInternetClient(**self.settings.internet.args.model_dump())
        elif self.settings.internet.type == INTERNET_CLIENT_BRAVE_TYPE:
            self.internet = BraveInternetClient(**self.settings.internet.args.model_dump())

        self.auth = AuthenticationClient(cache=self.cache, **self.settings.auth.args) if self.settings.auth else None

    def clear(self):
        self.search.close()
