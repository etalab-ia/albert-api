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

        self.cache = CacheManager(connection_pool=ConnectionPool(**self.settings.clients.cache.args))
        # @TODO: check if cache is reachable

        if self.settings.clients.search.type == SEARCH_CLIENT_ELASTIC_TYPE:
            self.search = ElasticSearchClient(models=self.models, **self.settings.clients.search.args)
        elif self.settings.clients.search.type == SEARCH_CLIENT_QDRANT_TYPE:
            self.search = QdrantSearchClient(models=self.models, **self.settings.clients.search.args)

        if self.settings.clients.internet.type == INTERNET_CLIENT_DUCKDUCKGO_TYPE:
            self.internet = DuckDuckGoInternetClient(**self.settings.clients.internet.args)
        elif self.settings.clients.internet.type == INTERNET_CLIENT_BRAVE_TYPE:
            self.internet = BraveInternetClient(**self.settings.clients.internet.args)

        self.auth = AuthenticationClient(cache=self.cache, **self.settings.clients.auth.args) if self.settings.clients.auth else None

    def clear(self):
        self.search.close()
