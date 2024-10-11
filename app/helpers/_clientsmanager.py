from redis import Redis as CacheManager
from redis.connection import ConnectionPool

from app.schemas.config import Config

from ._modelclients import ModelClients
from ._authenticationclient import AuthenticationClient
from .searchclients._searchclient import SearchClient


class ClientsManager:
    def __init__(self, config: Config):
        self.config = config

    def set(self):
        # set models
        self.models = ModelClients(config=self.config)

        # set cache
        self.cache = CacheManager(connection_pool=ConnectionPool(**self.config.databases.cache.args))

        # set search
        self.search = SearchClient.import_constructor(self.config.databases.search.type)(models=self.models, **self.config.databases.search.args)

        # set auth
        self.auth = AuthenticationClient(cache=self.cache, **self.config.auth.args) if self.config.auth else None

    def clear(self):
        self.vectors.close()
