from fastapi.testclient import TestClient
import pytest

from app.schemas.models import Model, Models
from app.utils.configuration import configuration
from app.utils.variables import ENDPOINT__MODELS


@pytest.mark.usefixtures("client")
class TestModels:
    def test_get_models_response_status_code(self, client: TestClient):
        """Test the GET /models response status code."""
        response = client.get_without_permissions(url=f"/v1{ENDPOINT__MODELS}")
        assert response.status_code == 200, f"error: retrieve models ({response.status_code})"

        models = Models(data=[Model(**model) for model in response.json()["data"]])
        assert isinstance(models, Models)
        assert all(isinstance(model, Model) for model in models.data)

        model = models.data[0].id
        response = client.get_without_permissions(url=f"/v1{ENDPOINT__MODELS}/{model}")
        assert response.status_code == 200, f"error: retrieve model ({response.status_code})"

        model = Model(**response.json())
        assert isinstance(model, Model)

    def test_get_models_non_existing_model(self, client: TestClient):
        """Test the GET /models response status code for a non-existing model."""
        response = client.get_without_permissions(url=f"/v1{ENDPOINT__MODELS}/non-existing-model")
        assert response.status_code == 404, f"error: retrieve non-existing model ({response.status_code})"

    def test_get_models_aliases(self, client: TestClient):
        """Test the GET /models response status code for a non-existing model."""
        model = configuration.models[0]

        response = client.get_without_permissions(url=f"/v1{ENDPOINT__MODELS}/{model.name}")
        assert response.json()["aliases"] == model.aliases

        response = client.get_without_permissions(url=f"/v1{ENDPOINT__MODELS}/{model.aliases[0]}")
        assert response.json()["id"] == model.name
