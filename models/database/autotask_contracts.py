from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from .base import Base
from sqlalchemy.orm import Mapped, mapped_column

class Autotask_Contracts(Base):
    __tablename__ = '_autotask_contracts'
    primary_key = Column(Integer, primary_key=True)
    autotask_id = Column(Integer)
    company_key:Mapped[int] = mapped_column(ForeignKey("companies.primary_key"))
    startDate = Column(DateTime)
    endDate = Column(DateTime)
    contractName = Column(String)
    autotask_tenant_key: Mapped[int] = mapped_column(ForeignKey("autotask_tenants.primary_key"))
