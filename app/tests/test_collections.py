import time
from uuid import uuid4

from fastapi.testclient import TestClient
import pytest

from app.schemas.collections import Collection, Collections, CollectionVisibility
from app.utils.variables import ENDPOINT__COLLECTIONS


@pytest.mark.usefixtures("client")
class TestCollections:
    def test_create_private_collection(self, client: TestClient):
        params = {"name": f"test_collection_{str(uuid4())}", "visibility": CollectionVisibility.PRIVATE}
        response = client.post_without_permissions(url=f"/v1{ENDPOINT__COLLECTIONS}", json=params)
        assert response.status_code == 201, response.text

        collection_id = response.json()["id"]

        response = client.get_without_permissions(url=f"/v1{ENDPOINT__COLLECTIONS}")
        assert response.status_code == 200, response.text

        collections = response.json()
        Collections(**collections)  # test output format

        collections = [collection for collection in collections["data"] if collection["id"] == collection_id]
        assert len(collections) == 1

        collection = collections[0]
        assert collection["name"] == params["name"]
        assert collection["visibility"] == CollectionVisibility.PRIVATE

    def test_get_one_collection(self, client: TestClient):
        collection_name = f"test_collection_{str(uuid4())}"
        params = {"name": collection_name, "visibility": CollectionVisibility.PRIVATE}
        response = client.post_without_permissions(url=f"/v1{ENDPOINT__COLLECTIONS}", json=params)
        assert response.status_code == 201, response.text

        collection_id = response.json()["id"]

        response = client.get_without_permissions(url=f"/v1{ENDPOINT__COLLECTIONS}/{collection_id}")
        assert response.status_code == 200, response.text

        collection = response.json()
        assert collection["name"] == collection_name

    def test_patch_collection_name(self, client: TestClient):
        collection_name = f"test_collection_{str(uuid4())}"
        params = {"name": collection_name, "visibility": CollectionVisibility.PRIVATE}
        response = client.post_without_permissions(url=f"/v1{ENDPOINT__COLLECTIONS}", json=params)
        assert response.status_code == 201, response.text

        collection_id = response.json()["id"]
        new_collection_name = f"test_collection_{str(uuid4())}"
        params = {"name": new_collection_name}
        response = client.patch_without_permissions(url=f"/v1{ENDPOINT__COLLECTIONS}/{collection_id}", json=params)
        assert response.status_code == 204, response.text

        response = client.get_without_permissions(url=f"/v1{ENDPOINT__COLLECTIONS}/{collection_id}")
        assert response.status_code == 200, response.text

        collection = response.json()
        assert collection["name"] == new_collection_name

    def test_format_collection(self, client: TestClient):
        params = {"name": f"test_collection_{str(uuid4())}", "visibility": CollectionVisibility.PRIVATE}
        response = client.post_without_permissions(url=f"/v1{ENDPOINT__COLLECTIONS}", json=params)
        assert response.status_code == 201, response.text
        collection_id = response.json()["id"]

        response = client.get_without_permissions(url=f"/v1{ENDPOINT__COLLECTIONS}")
        assert response.status_code == 200, response.text

        collections = response.json()
        Collections(**collections)  # test output format

        response = client.get_without_permissions(url=f"/v1{ENDPOINT__COLLECTIONS}/{collection_id}")
        assert response.status_code == 200, response.text

        collection = response.json()
        Collection(**collection)  # test output format

        response = client.get_without_permissions(url=f"/v1{ENDPOINT__COLLECTIONS}/{collection_id}")
        assert response.status_code == 200, response.text

        collection = response.json()
        Collection(**collection)  # test output format

    def test_create_public_collection_without_permissions(self, client: TestClient):
        params = {"name": f"test_collection_{str(uuid4())}", "visibility": CollectionVisibility.PUBLIC}
        response = client.post_without_permissions(url=f"/v1{ENDPOINT__COLLECTIONS}", json=params)
        assert response.status_code == 403, response.text

    def test_patch_public_collection_without_permissions(self, client: TestClient):
        params = {"name": f"test_collection_{str(uuid4())}", "visibility": CollectionVisibility.PUBLIC}
        response = client.post_without_permissions(url=f"/v1{ENDPOINT__COLLECTIONS}", json=params)
        assert response.status_code == 403, response.text

    def test_create_public_collection_with_permissions(self, client: TestClient):
        collection_name = f"test_collection_{str(uuid4())}"
        params = {"name": collection_name, "visibility": CollectionVisibility.PUBLIC}
        response = client.post_with_permissions(url=f"/v1{ENDPOINT__COLLECTIONS}", json=params)
        assert response.status_code == 201, response.text

        collection_id = response.json()["id"]

        response = client.get_without_permissions(url=f"/v1{ENDPOINT__COLLECTIONS}")
        assert response.status_code == 200, response.text

        collections = response.json()
        collections = [collection for collection in collections["data"] if collection["id"] == collection_id]
        assert len(collections) == 1

        collection = collections[0]
        assert collection["name"] == collection_name
        assert collection["visibility"] == CollectionVisibility.PUBLIC

    def test_patch_public_collection_with_permissions(self, client: TestClient):
        collection_name = f"test_collection_{str(uuid4())}"
        params = {"name": collection_name, "visibility": CollectionVisibility.PRIVATE}
        response = client.post_with_permissions(url=f"/v1{ENDPOINT__COLLECTIONS}", json=params)
        assert response.status_code == 201, response.text

        collection_id = response.json()["id"]

        params = {"visibility": CollectionVisibility.PUBLIC}
        response = client.patch_with_permissions(url=f"/v1{ENDPOINT__COLLECTIONS}/{collection_id}", json=params)
        assert response.status_code == 204, response.text

    def test_view_collection_of_other_user(self, client: TestClient):
        collection_name = f"test-collection_{str(uuid4())}"
        params = {"name": collection_name, "visibility": CollectionVisibility.PRIVATE}
        response = client.post_with_permissions(url=f"/v1{ENDPOINT__COLLECTIONS}", json=params)
        assert response.status_code == 201, response.text

        collection_id = response.json()["id"]

        response = client.get_without_permissions(url=f"/v1{ENDPOINT__COLLECTIONS}/{collection_id}")
        assert response.status_code == 404, response.text

    def test_view_public_collection_of_other_user(self, client: TestClient):
        collection_name = f"test-collection_{str(uuid4())}"
        params = {"name": collection_name, "visibility": CollectionVisibility.PUBLIC}
        response = client.post_with_permissions(url=f"/v1{ENDPOINT__COLLECTIONS}", json=params)
        assert response.status_code == 201, response.text

        collection_id = response.json()["id"]

        response = client.get_without_permissions(url=f"/v1{ENDPOINT__COLLECTIONS}/{collection_id}")
        assert response.status_code == 200, response.text

    def test_delete_private_collection_without_permissions(self, client: TestClient):
        collection_name = f"test-collection_{str(uuid4())}"
        params = {"name": collection_name, "visibility": CollectionVisibility.PRIVATE}
        response = client.post_without_permissions(url=f"/v1{ENDPOINT__COLLECTIONS}", json=params)
        assert response.status_code == 201, response.text

        collection_id = response.json()["id"]

        response = client.delete_without_permissions(url=f"/v1{ENDPOINT__COLLECTIONS}/{collection_id}")
        assert response.status_code == 204

        response = client.get_without_permissions(url=f"/v1{ENDPOINT__COLLECTIONS}")
        collections = response.json()
        assert response.status_code == 200, response.text

        collections = [collection for collection in collections["data"] if collection["id"] == collection_id]
        assert len(collections) == 0

    def test_delete_public_collection_without_permissions(self, client: TestClient):
        collection_name = f"test-collection_{str(uuid4())}"
        params = {"name": collection_name, "visibility": CollectionVisibility.PUBLIC}
        response = client.post_with_permissions(url=f"/v1{ENDPOINT__COLLECTIONS}", json=params)
        assert response.status_code == 201, response.text

        collection_id = response.json()["id"]

        response = client.get_without_permissions(url=f"/v1{ENDPOINT__COLLECTIONS}/{collection_id}")
        collections = response.json()
        assert response.status_code == 200, response.text

        response = client.delete_without_permissions(url=f"/v1{ENDPOINT__COLLECTIONS}/{collection_id}")
        assert response.status_code == 404, response.text

    def test_delete_public_collection_with_permissions(self, client: TestClient):
        collection_name = f"test-collection_{str(uuid4())}"
        params = {"name": collection_name, "visibility": CollectionVisibility.PUBLIC}
        response = client.post_with_permissions(url=f"/v1{ENDPOINT__COLLECTIONS}", json=params)
        assert response.status_code == 201, response.text

        collection_id = response.json()["id"]

        response = client.delete_with_permissions(url=f"/v1{ENDPOINT__COLLECTIONS}/{collection_id}")
        assert response.status_code == 204, response.text

        response = client.get_without_permissions(url=f"/v1{ENDPOINT__COLLECTIONS}")
        collections = response.json()
        assert response.status_code == 200, response.text

        collections = [collection["id"] for collection in collections["data"] if collection["id"] == collection_id]
        assert len(collections) == 0

    def test_create_collection_with_empty_name(self, client: TestClient):
        collection_name = " "
        params = {"name": collection_name, "visibility": CollectionVisibility.PRIVATE}
        response = client.post_without_permissions(url=f"/v1{ENDPOINT__COLLECTIONS}", json=params)
        assert response.status_code == 422, response.text

    def test_create_collection_with_description(self, client: TestClient):
        params = {"name": f"test_collection_{str(uuid4())}", "visibility": CollectionVisibility.PRIVATE, "description": "test-description"}
        response = client.post_without_permissions(url=f"/v1{ENDPOINT__COLLECTIONS}", json=params)
        assert response.status_code == 201, response.text

        collection_id = response.json()["id"]

        response = client.get_without_permissions(url=f"/v1{ENDPOINT__COLLECTIONS}/{collection_id}")
        assert response.status_code == 200, response.text

        collection = response.json()

        assert collection["description"] == params["description"]

    def test_update_collection_updated_at(self, client: TestClient):
        params = {"name": f"test_collection_{str(uuid4())}", "visibility": CollectionVisibility.PRIVATE}
        response = client.post_without_permissions(url=f"/v1{ENDPOINT__COLLECTIONS}", json=params)
        assert response.status_code == 201, response.text

        collection_id = response.json()["id"]

        response = client.get_without_permissions(url=f"/v1{ENDPOINT__COLLECTIONS}/{collection_id}")
        assert response.status_code == 200, response.text

        collection = response.json()
        assert collection["updated_at"] is not None
        updated_at = collection["updated_at"]

        time.sleep(1)

        response = client.patch_without_permissions(url=f"/v1{ENDPOINT__COLLECTIONS}/{collection_id}", json={"description": "test-description"})
        assert response.status_code == 204, response.text

        response = client.get_without_permissions(url=f"/v1{ENDPOINT__COLLECTIONS}/{collection_id}")
        assert response.status_code == 200, response.text

        collection = response.json()
        assert collection["updated_at"] is not None
        assert collection["updated_at"] > updated_at
