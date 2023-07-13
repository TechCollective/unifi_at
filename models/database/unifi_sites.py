from sqlalchemy import Column, Integer, String, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from .base import Base

# TODO Need a way to track different sites from different controllers.
class UniFi_Sites(Base):
    __tablename__ = 'unifi_sites'
    primary_key: Mapped[int] = mapped_column(Integer, primary_key=True)
    name = Column(String)
    id = Column(String)
    desc = Column(String)
    controller_key: Mapped[int] = mapped_column(ForeignKey("unifi_controllers.primary_key"))
    controller: Mapped["UniFi_Controllers"] = relationship(back_populates="sites")
