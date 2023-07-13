from sqlalchemy import Column, Integer, String
from .base import Base

class Autotask_Products(Base):
    __tablename__ = '_autotask_products'
    primary_key = Column(Integer, primary_key=True)
    id = Column(Integer)
    description = Column(String)
    manufacturerName = Column(String)
    manufacturerProductName = Column(String)
    productCategory = Column(String)