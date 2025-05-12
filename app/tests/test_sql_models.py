from datetime import datetime
import pytest
from typing import Tuple
from app.sql.models import Usage
from sqlalchemy import desc


class TestUsageModel:
    def test_create_log(self, db_session, users: Tuple[int, int], tokens: Tuple[int, int]):
        """Test creating a log entry"""

        user_with_permissions, user_without_permissions = users
        token_with_permissions, token_without_permissions = tokens

        log = Usage(
            user_id=user_with_permissions["id"],
            token_id=token_with_permissions["id"],
            endpoint="/test/endpoint",
            model="test_model",
            prompt_tokens=100,
            completion_tokens=0.5,
            total_tokens=50,
        )
        db_session.add(log)
        db_session.commit()

        saved_log = db_session.query(Usage).order_by(desc(Usage.datetime)).first()
        assert saved_log.user_id == user_with_permissions["id"]
        assert saved_log.token_id == token_with_permissions["id"]
        assert saved_log.endpoint == "/test/endpoint"
        assert saved_log.model == "test_model"
        assert saved_log.prompt_tokens == 100
        assert saved_log.completion_tokens == 0.5
        assert saved_log.total_tokens == 50
        assert isinstance(saved_log.datetime, datetime)

    def test_log_repr(self, db_session, users: Tuple[int, int], tokens: Tuple[int, int]):
        """Test the string representation of a log entry"""
        user_with_permissions, user_without_permissions = users
        token_with_permissions, token_without_permissions = tokens

        log = Usage(user_id=user_with_permissions["id"], token_id=token_with_permissions["id"], endpoint="/test/endpoint", model="test_model")
        db_session.add(log)
        db_session.commit()

        assert (
            str(log)
            == f"<Usage (id={log.id}, datetime={log.datetime}, user_id={user_with_permissions["id"]}, token_id={token_with_permissions["id"]}, endpoint=/test/endpoint, duration=None)>"
        )

    def test_nullable_fields(self, db_session, users: Tuple[int, int], tokens: Tuple[int, int]):
        """Test that optional fields can be null"""
        user_with_permissions, user_without_permissions = users
        token_with_permissions, token_without_permissions = tokens

        log = Usage(user_id=user_with_permissions["id"], token_id=token_with_permissions["id"], endpoint="/test/endpoint", model="test_model")
        db_session.add(log)
        db_session.commit()

        saved_log = db_session.query(Usage).order_by(desc(Usage.id)).first()
        assert saved_log.prompt_tokens is None
        assert saved_log.completion_tokens is None
        assert saved_log.total_tokens is None
        assert saved_log.duration is None

    def test_non_nullable_fields(self, db_session, users: Tuple[int, int], tokens: Tuple[int, int]):
        """Test that required fields cannot be null"""
        user_with_permissions, user_without_permissions = users
        token_with_permissions, token_without_permissions = tokens

        log = Usage(user_id=user_with_permissions["id"], token_id=token_with_permissions["id"], model="test_model")
        with pytest.raises(Exception):
            db_session.add(log)
            db_session.commit()
        db_session.rollback()
