import pytest

from app.schemas.models import Model, Models


@pytest.mark.usefixtures("args", "session")
class TestModels:
    def test_get_models_response_status_code(self, args, session):
        """Test the GET /models response status code."""
        response = session.get(f"{args['base_url']}/models")
        assert response.status_code == 200, f"error: retrieve models ({response.status_code})"

        models = Models(data=[Model(**model) for model in response.json()["data"]])
        assert isinstance(models, Models)
        assert all(isinstance(model, Model) for model in models.data)

    def test_get_model_retrieve_model(self, args, session):
        """Test the GET /models/{model_id} response status code."""
        response = session.get(f"{args['base_url']}/models")
        assert response.status_code == 200, f"error: retrieve models ({response.status_code})"

        model = response.json()["data"][0]["id"]      
        response = session.get(f"{args['base_url']}/models/{model}")
        assert response.status_code == 200, f"error: retrieve model ({response.status_code})"
        
        model = Model(**response.json())
        assert isinstance(model, Model)
    
    def test_get_models_non_existing_model(self, args, session):
        """Test the GET /models response status code for a non-existing model."""
        response = session.get(f"{args['base_url']}/models/non-existing-model")
        assert response.status_code == 404, f"error: retrieve non-existing model ({response.status_code})"
    
