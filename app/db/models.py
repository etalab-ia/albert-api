from datetime import datetime
from sqlalchemy import Column, DateTime, String, Integer, Float
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()


class Log(Base):
    __tablename__ = "logs"

    id = Column(Integer, primary_key=True)
    datetime = Column(DateTime, nullable=False, default=datetime.utcnow)
    user = Column(String, nullable=True)
    endpoint = Column(String, nullable=False)
    model = Column(String, nullable=True)
    prompt_tokens = Column(Integer)
    completion_tokens = Column(Float)
    total_tokens = Column(Integer)

    def __repr__(self):
        return f"<Log(datetime={self.datetime}, user={self.user}, endpoint={self.endpoint})>"
