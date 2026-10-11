from sqlalchemy import Column, Integer, String, DateTime, UniqueConstraint, func
from models.base import Base


class PartyStatus(Base):
    __tablename__ = "party_status"

    id = Column(Integer, primary_key=True)
    enumerator = Column(String(50), nullable=False)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())

    __table_args__ = (UniqueConstraint("enumerator"),)

    PENDING = "pending"
    ACTIVE = "active"
    REJECTED = "rejected"
