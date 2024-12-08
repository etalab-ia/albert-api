from redis import Redis as CacheManager
from redis.connection import ConnectionPool

from app.clients import AuthenticationClient, ModelClients
from app.clients._internetclient import InternetClient
from app.clients.searchclients import ElasticSearchClient, QdrantSearchClient
from app.schemas.settings import Settings
from app.utils.variables import SEARCH_ELASTIC_TYPE, SEARCH_QDRANT_TYPE


class ClientsManager:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    def set(self):
        self.models = ModelClients(settings=self.settings)

        self.cache = CacheManager(connection_pool=ConnectionPool(**self.settings.cache.args))

        if self.settings.search.type == SEARCH_ELASTIC_TYPE:
            self.search = ElasticSearchClient(models=self.models, **self.settings.search.args)
        elif self.settings.search.type == SEARCH_QDRANT_TYPE:
            self.search = QdrantSearchClient(models=self.models, **self.settings.search.args)

        self.internet = InternetClient(model_clients=self.models, search_client=self.search, **self.settings.internet.args.model_dump())

        self.auth = AuthenticationClient(cache=self.cache, **self.settings.auth.args) if self.settings.auth else None

    def clear(self):
        self.search.close()
