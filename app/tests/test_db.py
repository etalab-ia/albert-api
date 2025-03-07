from datetime import datetime
import pytest

from app.db.models import Usage
from sqlalchemy import desc


class TestLogModel:
    def test_create_log(self, db_session):
        """Test creating a log entry"""
        log = Usage(user="test_user", endpoint="/test/endpoint", model="test_model", prompt_tokens=100, completion_tokens=0.5, total_tokens=50)
        db_session.add(log)
        db_session.commit()

        saved_log = db_session.query(Usage).order_by(desc(Usage.id)).first()
        assert saved_log.user == "test_user"
        assert saved_log.endpoint == "/test/endpoint"
        assert saved_log.model == "test_model"
        assert saved_log.prompt_tokens == 100
        assert saved_log.completion_tokens == 0.5
        assert saved_log.total_tokens == 50
        assert isinstance(saved_log.datetime, datetime)

    def test_log_repr(self, db_session):
        """Test the string representation of a log entry"""
        log = Usage(user="test_user", endpoint="/test/endpoint", model="test_model")
        db_session.add(log)
        db_session.commit()

        assert str(log) == f"<Usage (id={log.id}, datetime={log.datetime}, user=test_user, endpoint=/test/endpoint, duration=None)>"

    def test_nullable_fields(self, db_session):
        """Test that optional fields can be null"""
        log = Usage(user="test_user", endpoint="/test/endpoint", model="test_model")
        db_session.add(log)
        db_session.commit()

        saved_log = db_session.query(Usage).order_by(desc(Usage.id)).first()
        assert saved_log.prompt_tokens is None
        assert saved_log.completion_tokens is None
        assert saved_log.total_tokens is None
        assert saved_log.duration is None

    def test_non_nullable_fields(self, db_session):
        """Test that required fields cannot be null"""
        log = Usage(model="test_model")
        with pytest.raises(Exception):
            db_session.add(log)
            db_session.commit()
        db_session.rollback()
