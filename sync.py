# =============================================================
# sync.py — ETL: DocuSign → SQL (incremental, idempotente)
# =============================================================
import json
import logging
from datetime import datetime, timedelta, timezone

from docusign_client import DocuSignClient
from models import Envelope, Recipient, SyncState, get_session
from config import INITIAL_LOOKBACK_DAYS

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
log = logging.getLogger(__name__)


# ── Helpers de data ───────────────────────────────────────────────────────────

def _parse_dt(value: str | None) -> datetime | None:
    """Converte string ISO 8601 do DocuSign em datetime (sem fuso)."""
    if not value:
        return None
    try:
        dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
        return dt.replace(tzinfo=None)   # armazena como UTC naive no SQL
    except ValueError:
        return None

def _hours_between(start: datetime | None, end: datetime | None) -> float | None:
    if start and end:
        delta = end - start
        return round(delta.total_seconds() / 3600, 2)
    return None


# ── Transformação de envelope ─────────────────────────────────────────────────

def _map_envelope(raw: dict) -> dict:
    created   = _parse_dt(raw.get("createdDateTime"))
    sent      = _parse_dt(raw.get("sentDateTime"))
    completed = _parse_dt(raw.get("completedDateTime"))

    return dict(
        envelope_id   = raw["envelopeId"],
        status        = raw.get("status"),
        subject       = raw.get("emailSubject"),
        sender_name   = raw.get("sender", {}).get("userName"),
        sender_email  = raw.get("sender", {}).get("email"),
        created_at    = created,
        sent_at       = sent,
        delivered_at  = _parse_dt(raw.get("deliveredDateTime")),
        completed_at  = completed,
        voided_at     = _parse_dt(raw.get("voidedDateTime")),
        void_reason   = raw.get("voidedReason"),
        hours_to_sign = _hours_between(sent, completed),
        raw_json      = json.dumps(raw, ensure_ascii=False),
        synced_at     = datetime.utcnow(),
    )


# ── Transformação de destinatários ────────────────────────────────────────────

def _map_recipients(envelope_id: str, recipients_data: dict) -> list[dict]:
    rows = []
    # Percorre todos os tipos de destinatário (signers, carbonCopies, etc.)
    for recip_type in ("signers", "carbonCopies", "certifiedDeliveries", "agents"):
        for r in recipients_data.get(recip_type, []):
            sent      = _parse_dt(r.get("sentDateTime"))
            signed    = _parse_dt(r.get("signedDateTime"))
            delivered = _parse_dt(r.get("deliveredDateTime"))
            declined  = _parse_dt(r.get("declinedDateTime"))

            rows.append(dict(
                envelope_id    = envelope_id,
                recipient_id   = r.get("recipientId"),
                name           = r.get("name"),
                email          = r.get("email"),
                role_name      = r.get("roleName"),
                status         = r.get("status"),
                routing_order  = int(r.get("routingOrder", 0)),
                sent_at        = sent,
                delivered_at   = delivered,
                signed_at      = signed,
                declined_at    = declined,
                decline_reason = r.get("declinedReason"),
                hours_to_sign  = _hours_between(sent, signed),
            ))
    return rows


# ── Upsert genérico ───────────────────────────────────────────────────────────

def _upsert_envelope(session, data: dict):
    obj = session.query(Envelope).filter_by(envelope_id=data["envelope_id"]).first()
    if obj:
        for k, v in data.items():
            setattr(obj, k, v)
    else:
        session.add(Envelope(**data))

def _upsert_recipient(session, data: dict):
    obj = session.query(Recipient).filter_by(
        envelope_id=data["envelope_id"],
        recipient_id=data["recipient_id"],
    ).first()
    if obj:
        for k, v in data.items():
            setattr(obj, k, v)
    else:
        session.add(Recipient(**data))


# ── Estado de sincronização ───────────────────────────────────────────────────

def _get_last_sync(session) -> datetime:
    row = session.query(SyncState).filter_by(key="last_sync_at").first()
    if row:
        return datetime.fromisoformat(row.value)
    # Primeira execução: busca os últimos N dias
    return datetime.utcnow() - timedelta(days=INITIAL_LOOKBACK_DAYS)

def _set_last_sync(session, dt: datetime):
    row = session.query(SyncState).filter_by(key="last_sync_at").first()
    if row:
        row.value = dt.isoformat()
    else:
        session.add(SyncState(key="last_sync_at", value=dt.isoformat()))


# ── Função principal de sync ──────────────────────────────────────────────────

def run_sync():
    log.info("Iniciando sincronização DocuSign → SQL")
    session = get_session()
    client  = DocuSignClient()

    # Determina o ponto de partida
    from_date = _get_last_sync(session)
    log.info(f"Buscando envelopes alterados desde {from_date.strftime('%Y-%m-%d %H:%M')} UTC")

    envelopes = client.list_envelopes(from_date=from_date)
    log.info(f"{len(envelopes)} envelopes encontrados")

    synced = 0
    errors = 0

    for raw in envelopes:
        eid = raw.get("envelopeId", "?")
        try:
            # Envelope
            env_data = _map_envelope(raw)
            _upsert_envelope(session, env_data)

            # Destinatários (já vêm no payload quando include=recipients)
            recip_data = raw.get("recipients") or client.get_recipients(eid)
            for r in _map_recipients(eid, recip_data):
                _upsert_recipient(session, r)

            synced += 1

        except Exception as exc:
            log.error(f"Erro no envelope {eid}: {exc}")
            errors += 1

    # Salva checkpoint ANTES do commit (se commit falhar, retentamos na próxima)
    _set_last_sync(session, datetime.utcnow())
    session.commit()
    session.close()

    log.info(
        f"Sincronização concluída — {synced} envelopes gravados, {errors} erros."
    )


if __name__ == "__main__":
    run_sync()
