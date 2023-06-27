from sqlalchemy import Column, Integer, String
from .base import Base

class Autotask_Companies(Base):
    __tablename__ = '_autotask_companies'
    primary_key = Column(Integer, primary_key=True)
    id = Column(Integer, unique=True)
    company_name = Column(String)
