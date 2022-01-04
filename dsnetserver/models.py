from sqlalchemy import Column, Integer, DateTime, Text, String, LargeBinary
from sqlalchemy.orm import declarative_base

Base = declarative_base()


class BroadcastQuery(Base):
    __tablename__ = 'broadcast_query'
    id = Column(Integer, primary_key=True)
    received_at = Column(DateTime(), index=True)
    message = Column(Text, nullable=False)


class PigeonHoleMessage(Base):
    __tablename__ = 'pigeonhole_message'
    id = Column(Integer, primary_key=True)
    received_at = Column(DateTime(), index=True)
    address = Column(String(64), index=True, nullable=False)
    message = Column(LargeBinary, nullable=False)
