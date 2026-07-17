from sqlalchemy import Column, Integer, String, Float, DateTime, JSON
from sqlalchemy.sql import func
from src.infrastructure.database import Base


class MetricModel(Base):
    """SQLAlchemy ORM model for the 'metrics' table."""
    __tablename__ = "metrics"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    value = Column(Float, nullable=False)
    timestamp = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    service = Column(String, nullable=False)
    tags = Column(JSON, nullable=False, default={})