from fastapi.testclient import TestClient

from app.main import app


def test_get_models():
    with TestClient(app) as client:
        response = client.get("/v1/models")
        assert response.status_code == 200
