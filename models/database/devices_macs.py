from typing import List
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from .base import Base

class Devices_Macs(Base):
    __tablename__ = 'devices_macs'
    primary_key: Mapped[int] = mapped_column(primary_key=True)
    mac_addresses = Column(String, nullable=False)
    device_key: Mapped[int] = mapped_column(ForeignKey("devices.primary_key"))
    device: Mapped["Devices"] = relationship(back_populates="macs")


