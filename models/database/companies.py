from typing import List
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from .base import Base

class Companies(Base):
    __tablename__ = 'companies'
    primary_key: Mapped[int] = mapped_column(primary_key=True)
    company_name = Column(String)
    company_number = Column(String)

