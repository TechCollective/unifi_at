from sqlalchemy import Column, Integer, String
from .base import Base

class Link_UniFi_Sites(Base):
    __tablename__ = 'link_unifi_sites'
    primary_key = Column(Integer, primary_key=True)
    companies_key = Column(String)
    unifi_sites_key = Column(String)