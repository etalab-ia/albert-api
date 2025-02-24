import pytest

from app.schemas.models import Model, Models
from app.utils.settings import settings


@pytest.mark.usefixtures("args", "test_client")
class TestModels:
    def test_get_models_response_status_code(self, args, test_client):
        """Test the GET /models response status code."""
        test_client.headers = {"Authorization": f"Bearer {args['api_key_admin']}"}
        response = test_client.get(f"{args['base_url']}/models")
        assert response.status_code == 200, f"error: retrieve models ({response.status_code})"

        models = Models(data=[Model(**model) for model in response.json()["data"]])
        assert isinstance(models, Models)
        assert all(isinstance(model, Model) for model in models.data)

        model = models.data[0].id
        response = test_client.get(f"{args['base_url']}/models/{model}")
        assert response.status_code == 200, f"error: retrieve model ({response.status_code})"

        model = Model(**response.json())
        assert isinstance(model, Model)

    def test_get_models_non_existing_model(self, args, test_client):
        """Test the GET /models response status code for a non-existing model."""
        test_client.headers = {"Authorization": f"Bearer {args['api_key_admin']}"}
        response = test_client.get(f"{args['base_url']}/models/non-existing-model")
        assert response.status_code == 404, f"error: retrieve non-existing model ({response.status_code})"

    def test_get_models_aliases(self, args, test_client):
        """Test the GET /models response status code for a non-existing model."""
        test_client.headers = {"Authorization": f"Bearer {args['api_key_admin']}"}
        model = settings.models[0]

        response = test_client.get(f"{args['base_url']}/models/{model.id}")
        assert response.json()["aliases"] == model.aliases

        response = test_client.get(f"{args['base_url']}/models/{model.aliases[0]}")
        assert response.json()["id"] == model.id

    # @TODO: move to test_chat.py
    # def test_get_models_rate_limit(self, args, session_user):
    #     """Test the GET /models rate limiting."""
    #     start = time.time()
    #     i = 0
    #     check = False
    #     while time.time() - start < 60:
    #         i += 1
    #         response = session_user.get(f"{args["base_url"]}/models")
    #         if response.status_code == 429:
    #             check = True
    #             break
    #         else:
    #             assert response.status_code == 200

    #     assert check
