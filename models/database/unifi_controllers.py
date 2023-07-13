from typing import List
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from .base import Base

class UniFi_Controllers(Base):
    __tablename__ = 'unifi_controllers'
    primary_key: Mapped[int] = mapped_column(primary_key=True)
    host = Column(String, unique=True) #fqhn
    port = Column(Integer)
    last_full_sync = Column(DateTime)
    sites: Mapped[List["UniFi_Sites"]] = relationship(back_populates="controller")
    
