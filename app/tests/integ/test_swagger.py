from fastapi.testclient import TestClient
import pytest

from app.utils.settings import settings


@pytest.mark.usefixtures("client")
class TestSwagger:
    def test_swagger(self, client: TestClient):
        """Test the GET /swagger response status code."""
        response = client.get_without_permissions(url=settings.general.docs_url)
        assert response.status_code == 200, response.text

        response = client.get_without_permissions(url=settings.general.openapi_url)
        assert response.status_code == 200, response.text
