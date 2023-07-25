from typing import List
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from .base import Base

class Devices(Base):
    __tablename__ = 'devices'
    primary_key: Mapped[int] = mapped_column(primary_key=True)
    name = Column(String)
    description = Column(String)
    serial = Column(String)
    ip_addresses = Column(String)
    macs: Mapped[List["Devices_Macs"]] = relationship(back_populates="device")
    manufacturer = Column(String)
    model = Column(String)
    company_key: Mapped[int] = mapped_column(ForeignKey("companies.primary_key"))
    install_date = Column(DateTime)

    def __repr__(self):
        return f"Devices(id={self.primary_key}, name='{self.name}', serial='{self.serial}', ip_addresses='{self.ip_addresses}', manufacturer='{self.manufacturer}', model='{self.model}')"