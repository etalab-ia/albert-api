from redis import Redis as CacheManager
from redis.connection import ConnectionPool


from app.schemas.config import Settings

from ._modelclients import ModelClients
from ._authenticationclient import AuthenticationClient
from .searchclients._searchclient import SearchClient


class ClientsManager:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    def set(self):
        # set models
        self.models = ModelClients(settings=self.settings)

        # set cache
        self.cache = CacheManager(connection_pool=ConnectionPool(**self.settings.cache.args))

        # set search
        self.search = SearchClient.import_constructor(self.search.type)(models=self.models, **self.search.args)

        # set auth
        self.auth = AuthenticationClient(cache=self.cache, **self.settings.auth.args) if self.settings.auth else None

    def clear(self):
        self.search.close()
