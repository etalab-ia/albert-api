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

        assert client_1.api_url != client_2.api_url
        assert client_1.api_url == client_3.api_url
