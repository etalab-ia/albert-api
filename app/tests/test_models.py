import time

import pytest

from app.schemas.models import Model, Models
from app.utils.settings import settings


@pytest.mark.usefixtures("args", "session_user", "session_admin")
class TestModels:
    def test_get_models_response_status_code(self, args, session_admin):
        """Test the GET /models response status code."""
        response = session_admin.get(f"{args["base_url"]}/models")
        assert response.status_code == 200, f"error: retrieve models ({response.status_code})"

        models = Models(data=[Model(**model) for model in response.json()["data"]])
        assert isinstance(models, Models)
        assert all(isinstance(model, Model) for model in models.data)

        model = models.data[0].id
        response = session_admin.get(f"{args["base_url"]}/models/{model}")
        assert response.status_code == 200, f"error: retrieve model ({response.status_code})"

        model = Model(**response.json())
        assert isinstance(model, Model)

    def test_get_models_non_existing_model(self, args, session_admin):
        """Test the GET /models response status code for a non-existing model."""
        response = session_admin.get(f"{args["base_url"]}/models/non-existing-model")
        assert response.status_code == 404, f"error: retrieve non-existing model ({response.status_code})"

    def test_get_models_aliases(self, args, session_admin):
        """Test the GET /models response status code for a non-existing model."""

        model = settings.models[0]

        response = session_admin.get(f"{args["base_url"]}/models/{model.id}")
        assert response.json()["aliases"] == model.aliases

        response = session_admin.get(f"{args["base_url"]}/models/{model.aliases[0]}")
        assert response.json()["id"] == model.id

    def test_get_models_rate_limit(self, args, session_user):
        """Test the GET /models rate limiting."""
        start = time.time()
        i = 0
        check = False
        while time.time() - start < 60:
            i += 1
            response = session_user.get(f"{args["base_url"]}/models")
            if response.status_code == 429:
                check = True
                break
            else:
                assert response.status_code == 200

        assert check
