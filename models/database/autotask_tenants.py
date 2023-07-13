from typing import List
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from .base import Base

class Autotask_Tenants(Base):
    __tablename__ = 'autotask_tenants'
    primary_key = Column(Integer, primary_key=True)
    host = Column(String)
    api_user = Column(String, unique=True)
    last_sync = Column(DateTime)
    last_full_sync = Column(DateTime)
    

    