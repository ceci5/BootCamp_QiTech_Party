from sqlalchemy import CHAR, Column, DateTime, ForeignKey, Integer, Numeric, UniqueConstraint, func
from sqlalchemy.orm import relationship
from models.base import Base
from models import Party


class Client(Base):
    """Uma pessoa jurídica que é cliente da plataforma (guia §4; 01b §2).

    Não tem estado próprio: o estado que vale é o da parte por trás dela
    (06 §3). Por isso não há tabela de status nem de evento aqui — só a
    ligação com a parte, uma por parte, e o preço.

    O percentual é Numeric, que o SQLAlchemy entrega como Decimal: é o
    preço que a plataforma cobra deste cliente, e preço não passa por
    float (regras do repositório, "Dinheiro").
    """

    __tablename__ = "client"

    id = Column(Integer, primary_key=True)
    client_key = Column(CHAR(36), nullable=False)
    party_id = Column(Integer, ForeignKey(Party.id), nullable=False)
    platform_fee_percentage = Column(Numeric(7, 4), nullable=False)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())

    __table_args__ = (
        UniqueConstraint("client_key"),
        UniqueConstraint("party_id"),
    )

    party = relationship("Party", foreign_keys=[party_id], back_populates="client", lazy="selectin")
