from redis import Redis as CacheManager
from redis.connection import ConnectionPool


from app.schemas.settings import Settings

from ._modelclients import ModelClients
from ._authenticationclient import AuthenticationClient
from ._internetclient import InternetClient
from .searchclients._searchclient import SearchClient


class ClientsManager:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    def set(self):
        self.models = ModelClients(settings=self.settings)

        self.cache = CacheManager(connection_pool=ConnectionPool(**self.settings.cache.args))

        self.search = SearchClient.import_constructor(self.settings.search.type)(models=self.models, **self.settings.search.args)

        self.internet = InternetClient(model_clients=self.models, search_client=self.search, **self.settings.internet.args)

        self.auth = AuthenticationClient(cache=self.cache, **self.settings.auth.args) if self.settings.auth else None

    def clear(self):
        self.search.close()
