from fastapi.testclient import TestClient
import pytest

from app.utils.configuration import configuration


@pytest.mark.usefixtures("client")
class TestSwagger:
    def test_swagger(self, client: TestClient):
        """Test the GET /swagger response status code."""
        response = client.get_without_permissions(url=configuration.settings.swagger_docs_url)
        assert response.status_code == 200, response.text

        response = client.get_without_permissions(url=configuration.settings.swagger_openapi_url)
        assert response.status_code == 200, response.text
