import pytest

from app.utils.lifespan import context


@pytest.mark.usefixtures("client")
class TestRouter:
    def test_get_model_client(self):
        # Get a language model with more than 1 client
        router = context.models(model="albert-small")

        # With roundrobin client should be different at each call
        client_1 = router.get_client(endpoint="")
        client_2 = router.get_client(endpoint="")
        client_3 = router.get_client(endpoint="")

        assert client_1.api_url != client_2.api_url
        assert client_1.api_url == client_3.api_url

    def test_get_model_client_with_queuing(self):
        router = context.models(model="albert-small-queuing")

        client = router.get_client(endpoint="")

        # For now the get_client method is not implemented
        assert client is None
