from sqlalchemy import Column, Integer, String, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from .base import Base
from models.database.unifi_controllers import UniFi_Controllers

# TODO Need a way to track different sites from different controllers.
class UniFi_Sites(Base):
    __tablename__ = 'unifi_sites'
    primary_key: Mapped[int] = mapped_column(Integer, primary_key=True)
    name = Column(String, nullable=False)
    id = Column(String, nullable=False)
    desc = Column(String, nullable=False)
    controller_key: Mapped[int] = mapped_column(ForeignKey("unifi_controllers.primary_key"))
    controller: Mapped["UniFi_Controllers"] = relationship(back_populates="sites")
