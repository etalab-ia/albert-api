import time

import pytest

from app.schemas.models import Model, Models
from app.utils.config import DEFAULT_RATE_LIMIT


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

    def test_get_models_rate_limit(self, args, session_user):
        """Test the GET /models rate limiting."""
        start = time.time()
        limit = int(DEFAULT_RATE_LIMIT.replace("/minute", ""))
        i = 0
        while time.time() - start < 60:
            i += 1
            response = session_user.get(f"{args["base_url"]}/models")
            if i == limit:
                assert response.status_code == 429
                break
            else:
                assert response.status_code == 200

        # sanity check to make sure the rate limiting is tested
        assert i == limit
