from sqlalchemy import Column, Integer, String
from .base import Base

class Autotask_CI_Types(Base):
    __tablename__ = '_autotask_ci_types'
    primary_key = Column(Integer, primary_key=True)
    value = Column(Integer)
    label = Column(String)