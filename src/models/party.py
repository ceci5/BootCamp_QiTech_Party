from sqlalchemy import CHAR, Column, DateTime, ForeignKey, Integer, String, UniqueConstraint, func
from sqlalchemy.orm import relationship
from models.base import Base
from models import PartyStatus


class Party(Base):
    """Uma pessoa física ou jurídica: a fonte única de identidade (guia §1).

    O documento guarda só dígitos — 11 para CPF, 14 para CNPJ — e é desse
    tamanho que sai o tipo da parte. O nome e o documento nunca saem desta
    API para os outros serviços (D0008): quem decide o que sai é o DTO.
    """

    __tablename__ = "party"

    id = Column(Integer, primary_key=True)
    party_key = Column(CHAR(36), nullable=False)
    party_status_id = Column(Integer, ForeignKey(PartyStatus.id), nullable=False)
    name = Column(String(255), nullable=False)
    document_number = Column(String(14), nullable=False)
    pix_key = Column(String(77), nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())

    __table_args__ = (
        UniqueConstraint("party_key"),
        UniqueConstraint("document_number"),
    )

    status = relationship("PartyStatus", foreign_keys=[party_status_id], lazy="selectin")

    status_events = relationship(
        "PartyStatusEvent",
        back_populates="party",
        order_by="asc(PartyStatusEvent.id)",
    )

    # O cliente da plataforma que esta parte é, se for (fatia 04): no
    # máximo um, pela UNIQUE(party_id) da tabela client.
    client = relationship("Client", back_populates="party", uselist=False, lazy="selectin")

    INDIVIDUAL = "individual"
    ORGANIZATION = "organization"
