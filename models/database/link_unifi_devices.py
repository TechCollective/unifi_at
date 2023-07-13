from typing import List
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from .base import Base

class Link_UniFi_Devices(Base):
    __tablename__ = 'link_unifi_devices'
    primary_key = Column(Integer, primary_key=True)
    device_key: Mapped[int] = mapped_column(ForeignKey("devices.primary_key"))
    unifi_sites_key: Mapped[int] = mapped_column(ForeignKey("unifi_sites.primary_key"))
    




