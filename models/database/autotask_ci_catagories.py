from sqlalchemy import Column, Integer, String
from .base import Base

class Autotask_CI_Catagories(Base):
    __tablename__ = '_autotask_ci_categories'
    primary_key = Column(Integer, primary_key=True)
    id = Column(Integer)
    name = Column(String)