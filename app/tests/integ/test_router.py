import pytest

from app.utils.context import global_context


@pytest.mark.usefixtures("client")
class TestModels:
    async def test_get_model_client(self):
        # Get a language model with more than 1 client
        router = await global_context.model_registry(model="albert-small")

        # With roundrobin client should be different at each call
        client_1 = router.get_client(endpoint="")
        client_2 = router.get_client(endpoint="")
        client_3 = router.get_client(endpoint="")

        assert client_1.timeout != client_2.timeout
        assert client_1.timeout == client_3.timeout
