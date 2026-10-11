from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, func
from sqlalchemy.orm import relationship
from models.base import Base
from models import Party, PartyStatus


class PartyStatusEvent(Base):
    """Uma linha da trilha de estado da parte. Append-only por gatilho.

    `from_status_id` é nulo no nascimento. `trace_id` é o X-Request-ID da
    requisição que causou a transição — o mesmo que o cliente recebeu de
    volta no cabeçalho da resposta.
    """

    __tablename__ = "party_status_event"

    id = Column(Integer, primary_key=True)
    party_id = Column(Integer, ForeignKey(Party.id), nullable=False)
    from_status_id = Column(Integer, ForeignKey(PartyStatus.id), nullable=True)
    to_status_id = Column(Integer, ForeignKey(PartyStatus.id), nullable=False)
    actor = Column(String(255), nullable=False)
    reason = Column(String(255), nullable=True)
    trace_id = Column(String(64), nullable=False)
    event_datetime = Column(DateTime(timezone=True), nullable=False)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())

    party = relationship(
        "Party",
        foreign_keys=[party_id],
        back_populates="status_events",
        lazy="selectin",
    )
    from_status = relationship("PartyStatus", foreign_keys=[from_status_id], lazy="selectin")
    to_status = relationship("PartyStatus", foreign_keys=[to_status_id], lazy="selectin")
