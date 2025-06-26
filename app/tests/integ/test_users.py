from datetime import datetime, timedelta, timezone
from http import HTTPMethod

from fastapi.testclient import TestClient
import pytest

from app.sql.models import Usage as UsageModel
from app.utils.variables import ENDPOINT__USERS_USAGE


@pytest.mark.usefixtures("client")
class TestUsers:
    def test_get_user_usage_authenticated(self, client: TestClient, users, tokens, db_session):
        """Test that authenticated users can access their usage data"""
        user_with_permissions, user_without_permissions = users
        token_with_permissions, token_without_permissions = tokens

        # Create test usage data for the user with permissions
        usage1 = UsageModel(
            user_id=user_with_permissions["id"],
            token_id=token_with_permissions["id"],
            endpoint="/test/endpoint1",
            method=HTTPMethod.POST,
            model="test_model_1",
            prompt_tokens=100,
            completion_tokens=50,
            total_tokens=150,
            cost=0.01,
            status=200,
        )

        usage2 = UsageModel(
            user_id=user_with_permissions["id"],
            token_id=token_with_permissions["id"],
            endpoint="/test/endpoint2",
            method=HTTPMethod.GET,
            model="test_model_2",
            prompt_tokens=200,
            completion_tokens=100,
            total_tokens=300,
            cost=0.02,
            status=200,
        )

        # Create usage data for another user (should not be returned)
        usage_other_user = UsageModel(
            user_id=user_without_permissions["id"],
            token_id=token_without_permissions["id"],
            endpoint="/test/endpoint3",
            method=HTTPMethod.POST,
            model="test_model_3",
            prompt_tokens=50,
            completion_tokens=25,
            total_tokens=75,
            cost=0.005,
            status=200,
        )

        # Add test data to database
        db_session.add(usage1)
        db_session.add(usage2)
        db_session.add(usage_other_user)
        db_session.commit()

        try:
            # Count actual usage records for the authenticated user in database
            expected_count = db_session.query(UsageModel).filter_by(user_id=user_with_permissions["id"]).count()

            # Test with authenticated user
            response = client.get_with_permissions(url=f"/v1{ENDPOINT__USERS_USAGE}")
            assert response.status_code == 200, response.text

            data = response.json()
            assert data["object"] == "list"
            assert "data" in data
            assert "total" in data
            assert "has_more" in data

            # Should only return data for the authenticated user
            assert len(data["data"]) == min(50, expected_count)  # Endpoint defaults to 50 records
            assert data["total"] == expected_count
            assert data["has_more"] is (expected_count > 50)

            # Verify the data belongs to the authenticated user
            for usage_record in data["data"]:
                assert usage_record["user_id"] == user_with_permissions["id"]

        finally:
            # Clean up test data
            db_session.query(UsageModel).filter(UsageModel.user_id.in_([user_with_permissions["id"], user_without_permissions["id"]])).delete()
            db_session.commit()

    def test_user_isolation(self, client: TestClient, users, tokens, db_session):
        """Test that a user can only access their own usage data"""
        user_with_permissions, user_without_permissions = users
        token_with_permissions, token_without_permissions = tokens

        # Create usage data for user without permissions
        usage_user2 = UsageModel(
            user_id=user_without_permissions["id"],
            token_id=token_without_permissions["id"],
            endpoint="/test/endpoint",
            method=HTTPMethod.POST,
            model="test_model",
            prompt_tokens=100,
            completion_tokens=50,
            total_tokens=150,
            cost=0.01,
            status=200,
        )

        # Create usage data for user with permissions
        usage_user1 = UsageModel(
            user_id=user_with_permissions["id"],
            token_id=token_with_permissions["id"],
            endpoint="/test/endpoint2",
            method=HTTPMethod.POST,
            model="test_model2",
            prompt_tokens=200,
            completion_tokens=100,
            total_tokens=300,
            cost=0.02,
            status=200,
        )

        db_session.add(usage_user1)
        db_session.add(usage_user2)
        db_session.commit()

        try:
            # User without permissions should only see their data
            response = client.get_without_permissions(url=f"/v1{ENDPOINT__USERS_USAGE}")
            assert response.status_code == 200, response.text

            data = response.json()
            # Count records for user without permissions
            user_without_count = db_session.query(UsageModel).filter_by(user_id=user_without_permissions["id"]).count()
            assert len(data["data"]) == user_without_count
            # Find the specific record we created in this test
            test_record = next((record for record in data["data"] if record["endpoint"] == "/test/endpoint"), None)
            assert test_record is not None, "Test record not found in response"
            assert test_record["user_id"] == user_without_permissions["id"]

            # User with permissions should only see their data
            response = client.get_with_permissions(url=f"/v1{ENDPOINT__USERS_USAGE}")
            assert response.status_code == 200, response.text

            data = response.json()
            # Count records for user with permissions
            user_with_count = db_session.query(UsageModel).filter_by(user_id=user_with_permissions["id"]).count()
            assert len(data["data"]) == user_with_count
            # Find the specific record we created in this test
            test_record = next((record for record in data["data"] if record["endpoint"] == "/test/endpoint2"), None)
            assert test_record is not None, "Test record not found in response"
            assert test_record["user_id"] == user_with_permissions["id"]

        finally:
            # Clean up test data
            db_session.query(UsageModel).filter(UsageModel.user_id.in_([user_with_permissions["id"], user_without_permissions["id"]])).delete()
            db_session.commit()

    def test_pagination_and_ordering(self, client: TestClient, users, tokens, db_session):
        """Test pagination and ordering parameters"""
        user_with_permissions, user_without_permissions = users
        token_with_permissions, token_without_permissions = tokens

        # Create multiple usage records with different timestamps and costs
        usage_records = []
        for i in range(5):
            usage = UsageModel(
                user_id=user_with_permissions["id"],
                token_id=token_with_permissions["id"],
                endpoint=f"/test/endpoint{i}",
                method=HTTPMethod.POST,
                model=f"test_model_{i}",
                prompt_tokens=100 + i * 10,
                completion_tokens=50 + i * 5,
                total_tokens=150 + i * 15,
                cost=0.01 + i * 0.01,
                status=200,
                datetime=datetime.now(timezone.utc) + timedelta(minutes=i),
            )
            usage_records.append(usage)
            db_session.add(usage)

        db_session.commit()

        try:
            # Count actual usage records for the user in database
            expected_total = db_session.query(UsageModel).filter_by(user_id=user_with_permissions["id"]).count()

            # Test default ordering (datetime desc) and limit
            response = client.get_with_permissions(url=f"/v1{ENDPOINT__USERS_USAGE}?limit=3")
            assert response.status_code == 200, response.text

            data = response.json()
            assert len(data["data"]) == min(3, expected_total)  # Should be limited to 3 or total records if less
            assert data["total"] == expected_total
            assert data["has_more"] is (expected_total > 3)

            # Verify descending order by datetime (most recent first)
            for i in range(len(data["data"]) - 1):
                current_timestamp = data["data"][i]["datetime"]
                next_timestamp = data["data"][i + 1]["datetime"]
                assert current_timestamp >= next_timestamp

            # Test ordering by cost ascending
            response = client.get_with_permissions(url=f"/v1{ENDPOINT__USERS_USAGE}?order_by=cost&order_direction=asc&limit=5")
            assert response.status_code == 200, response.text

            data = response.json()
            assert len(data["data"]) == min(5, expected_total)  # Should be limited to 5 or total records if less

            # Verify ascending order by cost
            for i in range(len(data["data"]) - 1):
                assert data["data"][i]["cost"] <= data["data"][i + 1]["cost"]

        finally:
            # Clean up test data
            db_session.query(UsageModel).filter(UsageModel.user_id == user_with_permissions["id"]).delete()
            db_session.commit()

    def test_unauthenticated_access_denied(self, client: TestClient):
        """Test that unauthenticated users cannot access usage data"""
        # Remove authorization header
        bearer = client.headers.pop("Authorization", None)
        response = client.get(url=f"/v1{ENDPOINT__USERS_USAGE}")
        assert response.status_code == 403, response.text
        bearer = client.headers.pop("Authorization", None)
        # Reset authorization header
        client.headers = {"Authorization": f"{bearer}"}

    def test_invalid_parameters(self, client: TestClient):
        """Test validation of query parameters"""

        # Test invalid limit (too high)
        response = client.get_with_permissions(url=f"/v1{ENDPOINT__USERS_USAGE}?limit=101")
        assert response.status_code == 422, response.text

        # Test invalid limit (too low)
        response = client.get_with_permissions(url=f"/v1{ENDPOINT__USERS_USAGE}?limit=0")
        assert response.status_code == 422, response.text

        # Test invalid order_by field
        response = client.get_with_permissions(url=f"/v1{ENDPOINT__USERS_USAGE}?order_by=invalid_field")
        assert response.status_code == 422, response.text

        # Test invalid order_direction
        response = client.get_with_permissions(url=f"/v1{ENDPOINT__USERS_USAGE}?order_direction=invalid")
        assert response.status_code == 422, response.text
