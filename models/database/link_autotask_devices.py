from typing import List
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from .base import Base

class Link_Autotask_Devices(Base):
    __tablename__ = 'link_autotask_devices'
    primary_key = Column(Integer, primary_key=True)
    device_key: Mapped[int] = mapped_column(ForeignKey("devices.primary_key"))
    autotask_tenant_key: Mapped[int] = mapped_column(ForeignKey("autotask_tenants.primary_key"))
    company_key:Mapped[int] = mapped_column(ForeignKey("companies.primary_key"))
    




