from sqlalchemy import Column, Integer, String
from .base import Base

class Link_Autotask_Companies(Base):
    __tablename__ = 'link_autotask_companies'
    primary_key = Column(Integer, primary_key=True)
    companies_key = Column(String)
    autotask_tenant_key = Column(String)
    id = Column(String)
