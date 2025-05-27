import pytest

from app.utils.context import global_context


@pytest.mark.usefixtures("client")
class TestRouter:
    def test_get_model_client(self):
        # Get a language model with more than 1 client
        router = global_context.models(model="albert-small")

        # With roundrobin client should be different at each call
        client_1 = router.get_client(endpoint="")
        client_2 = router.get_client(endpoint="")
        client_3 = router.get_client(endpoint="")

        assert client_1.timeout != client_2.timeout
        assert client_1.api_url != client_2.api_url or client_1.model != client_2.model
        assert client_1.api_url == client_3.api_url and client_1.model == client_3.model

    def test_get_model_client_with_queuing(self):
        router = global_context.models(model="albert-small-queuing")

        client = router.get_client(endpoint="")

        # For now the get_client method is not implemented
        assert client is None
