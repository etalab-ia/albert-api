from app.schemas.tools import Tool, Tools
import pytest


@pytest.mark.usefixtures("args", "session")
class TestTools:
    def test_get_tools_response_status_code(self, args, session):
        """Test the GET /tools response status code."""
        response = session.get(f"{args['base_url']}/tools")
        assert response.status_code == 200, f"error: retrieve tools ({response.status_code})"

    def test_get_tools_response_schemas(self, args, session):
        """Test the GET /tools response schemas."""
        response = session.get(f"{args['base_url']}/tools")
        response_json = response.json()

        tools = Tools(data=[Tool(**tool) for tool in response_json["data"]])

        assert isinstance(tools, Tools)
        assert all(isinstance(tool, Tool) for tool in tools.data)