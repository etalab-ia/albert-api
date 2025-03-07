from sqlalchemy import Column, DateTime, String, Integer, Float, func
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()


class Usage(Base):
    __tablename__ = "usages"

    id = Column(Integer, primary_key=True)
    datetime = Column(DateTime, nullable=False, default=func.now())
    duration = Column(Integer, nullable=True)
    user = Column(String, nullable=True)
    endpoint = Column(String, nullable=False)
    model = Column(String, nullable=True)
    prompt_tokens = Column(Integer)
    completion_tokens = Column(Float)
    total_tokens = Column(Integer)
    status = Column(Integer, nullable=True)

    def __repr__(self):
        return f"<Usage (id={self.id}, datetime={self.datetime}, user={self.user}, endpoint={self.endpoint}, duration={self.duration})>"
