from datetime import datetime
import pytest

from app.db.models import Log
from sqlalchemy import desc


class TestLogModel:
    def test_create_log(self, db_session):
        """Test creating a log entry"""
        log = Log(user="test_user", endpoint="/test/endpoint", model="test_model", token_per_sec=100, inter_token_latency=0.5, req_tokens_nb=50)
        db_session.add(log)
        db_session.commit()

        saved_log = db_session.query(Log).order_by(desc(Log.id)).first()
        assert saved_log.user == "test_user"
        assert saved_log.endpoint == "/test/endpoint"
        assert saved_log.model == "test_model"
        assert saved_log.token_per_sec == 100
        assert saved_log.inter_token_latency == 0.5
        assert saved_log.req_tokens_nb == 50
        assert isinstance(saved_log.datetime, datetime)

    def test_log_repr(self, db_session):
        """Test the string representation of a log entry"""
        log = Log(user="test_user", endpoint="/test/endpoint", model="test_model")
        db_session.add(log)
        db_session.commit()

        assert str(log) == f"<Log(datetime={log.datetime}, user=test_user, endpoint=/test/endpoint)>"

    def test_nullable_fields(self, db_session):
        """Test that optional fields can be null"""
        log = Log(user="test_user", endpoint="/test/endpoint", model="test_model")
        db_session.add(log)
        db_session.commit()

        saved_log = db_session.query(Log).order_by(desc(Log.id)).first()
        assert saved_log.token_per_sec is None
        assert saved_log.inter_token_latency is None
        assert saved_log.req_tokens_nb is None

    def test_non_nullable_fields(self, db_session):
        """Test that required fields cannot be null"""
        log = Log(model="test_model")
        with pytest.raises(Exception):
            db_session.add(log)
            db_session.commit()
