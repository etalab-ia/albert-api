import pytest

from app.schemas.core.settings import Model, ModelClient, ModelClientArgs


class TestModelSettings:
    def test_routing_strategy_validation(self):
        with pytest.raises(ValueError) as error_info:
            Model(
                id="model_router_1",
                type="text-generation",
                routing_strategy="no_strategy",
                clients=[ModelClient(model="model_1", type="albert", args=ModelClientArgs(api_url=""))],
            )

        assert "Input should be 'round_robin', 'shuffle' or 'least_busy'" in str(error_info.value)

        Model(
            id="model_router_1",
            type="text-generation",
            routing_strategy="shuffle",
            clients=[ModelClient(model="model_1", type="albert", args=ModelClientArgs(api_url=""))],
        )

        assert True

    def test_routing_model_validation(self):
        with pytest.raises(ValueError) as error_info:
            Model(
                id="model_router_1",
                type="text-generation",
                routing_mode="no_model",
                clients=[ModelClient(model="model_1", type="albert", args=ModelClientArgs(api_url=""))],
            )

        assert "Input should be 'queuing' or 'no_queuing'" in str(error_info.value)

        Model(
            id="model_router_1",
            type="text-generation",
            routing_model="queuing",
            clients=[ModelClient(model="model_1", type="albert", args=ModelClientArgs(api_url=""))],
        )

        assert True

    def test_routing_model_strategy_mapping_validation(self):
        # Expect test to fail because least_busy strategy cannot be used with no_queuing routing mode
        with pytest.raises(ValueError) as error_info:
            Model(
                id="model_router_1",
                type="text-generation",
                routing_strategy="least_busy",
                routing_mode="no_queuing",
                clients=[ModelClient(model="model_1", type="albert", args=ModelClientArgs(api_url=""))],
            )

        assert "Invalid routing mode: no_queuing for routing strategy least_busy" in str(error_info.value)

        Model(
            id="model_router_1",
            type="text-generation",
            routing_strategy="least_busy",
            routing_mode="queuing",
            clients=[ModelClient(model="model_1", type="albert", args=ModelClientArgs(api_url=""))],
        )

        assert True
