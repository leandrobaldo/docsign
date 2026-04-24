# =============================================================
# models.py — Tabelas SQL (SQLAlchemy ORM)
# =============================================================
from sqlalchemy import (
    create_engine, Column, String, DateTime,
    Float, Integer, Text, UniqueConstraint
)
from sqlalchemy.orm import declarative_base, sessionmaker
from config import DATABASE

Base = declarative_base()


class Envelope(Base):
    """
    Tabela principal — um registro por envelope DocuSign.
    É a tabela central para dashboards no Power BI.
    """
    __tablename__ = "envelopes"

    id              = Column(Integer, primary_key=True, autoincrement=True)
    envelope_id     = Column(String(100), unique=True, nullable=False, index=True)
    status          = Column(String(50))   # sent | delivered | completed | voided | declined
    subject         = Column(String(500))
    sender_name     = Column(String(200))
    sender_email    = Column(String(200))
    created_at      = Column(DateTime)
    sent_at         = Column(DateTime)
    delivered_at    = Column(DateTime)
    completed_at    = Column(DateTime)
    voided_at       = Column(DateTime)
    void_reason     = Column(Text)
    # Tempo até assinatura em horas (calculado pelo Python)
    hours_to_sign   = Column(Float)
    # Metadados extras em JSON bruto para análises avançadas
    raw_json        = Column(Text)
    synced_at       = Column(DateTime)     # última vez que esse registro foi atualizado


class Recipient(Base):
    """
    Tabela de destinatários — um registro por signatário por envelope.
    Permite análises de desempenho por pessoa/departamento.
    """
    __tablename__ = "recipients"
    __table_args__ = (
        UniqueConstraint("envelope_id", "recipient_id", name="uq_env_recip"),
    )

    id              = Column(Integer, primary_key=True, autoincrement=True)
    envelope_id     = Column(String(100), index=True)
    recipient_id    = Column(String(50))
    name            = Column(String(200))
    email           = Column(String(200))
    role_name       = Column(String(200))
    status          = Column(String(50))   # sent | delivered | completed | declined
    routing_order   = Column(Integer)
    sent_at         = Column(DateTime)
    delivered_at    = Column(DateTime)
    signed_at       = Column(DateTime)
    declined_at     = Column(DateTime)
    decline_reason  = Column(Text)
    hours_to_sign   = Column(Float)


class SyncState(Base):
    """
    Controla o estado da última sincronização para extrações incrementais.
    Evita rebuscar todos os envelopes a cada execução.
    """
    __tablename__ = "sync_state"

    id          = Column(Integer, primary_key=True, autoincrement=True)
    key         = Column(String(100), unique=True)
    value       = Column(String(500))


# ── Helpers ───────────────────────────────────────────────────────────────────

def get_engine():
    return create_engine(DATABASE["connection_string"], echo=False)

def get_session():
    engine = get_engine()
    Base.metadata.create_all(engine)   # cria as tabelas se não existirem
    Session = sessionmaker(bind=engine)
    return Session()
