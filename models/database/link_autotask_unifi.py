from sqlalchemy import Column, Integer, String
from sqlalchemy.orm import relationship
from .base import Base


class Link_Autotask_UniFi(Base):
    __tablename__ = 'link_autotask_unifi'
    primary_key = Column(Integer, primary_key=True)
    unifi_key = Column(String)
    autotask_key = Column(String)
