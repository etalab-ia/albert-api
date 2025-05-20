import pytest

from app.utils.lifespan import context


@pytest.mark.usefixtures("client")
class TestModels:
    def test_get_model_client(self):
        # Get a language model with more than 1 client
        router = context.models(model="albert-small")

        # With roundrobin client should be different at each call
        client_1 = router.get_client(endpoint="")
        client_2 = router.get_client(endpoint="")
        client_3 = router.get_client(endpoint="")

        assert client_1.timeout != client_2.timeout
        assert client_1.timeout == client_3.timeout
