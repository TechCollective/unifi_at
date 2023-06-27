from sqlalchemy import Column, Integer, String, DateTime
from .base import Base

class Autotask_Tenants(Base):
    __tablename__ = 'autotask_tenants'
    primary_key = Column(Integer, primary_key=True)
    host = Column(String)
    api_user = Column(String, unique=True)
    last_sync = Column(DateTime)