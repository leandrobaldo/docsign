# =============================================================
# docusign_client.py — Autenticação JWT + chamadas à API
# =============================================================
import time
import json
import requests
from datetime import datetime, timezone
from pathlib import Path
from jose import jwt as jose_jwt          # python-jose
from config import DOCUSIGN


# ── Autenticação JWT (Server-to-Server, sem browser) ─────────────────────────

def _build_jwt_token() -> str:
    """Gera um JWT assinado com a chave privada RSA para obter access token."""
    private_key = Path(DOCUSIGN["private_key_path"]).read_text()
    now = int(time.time())

    claims = {
        "iss": DOCUSIGN["integration_key"],
        "sub": DOCUSIGN["user_id"],
        "aud": DOCUSIGN["auth_server"],
        "iat": now,
        "exp": now + 3600,
        "scope": "signature impersonation",
    }

    return jose_jwt.encode(claims, private_key, algorithm="RS256")


def get_access_token() -> str:
    """
    Troca o JWT por um access token OAuth2.
    Na primeira execução você precisa ter concedido o consentimento em:
    https://account.docusign.com/oauth/auth?response_type=code
      &scope=signature%20impersonation&client_id=<INTEGRATION_KEY>
      &redirect_uri=https://www.docusign.com
    """
    jwt_token = _build_jwt_token()
    url = f"https://{DOCUSIGN['auth_server']}/oauth/token"

    response = requests.post(url, data={
        "grant_type": "urn:ietf:params:oauth:grant-type:jwt-bearer",
        "assertion": jwt_token,
    }, timeout=30)

    if response.status_code != 200:
        raise RuntimeError(
            f"Falha na autenticação DocuSign: {response.status_code} — {response.text}"
        )

    return response.json()["access_token"]


# ── Cliente da API ────────────────────────────────────────────────────────────

class DocuSignClient:
    """
    Wrapper simplificado sobre a eSignature REST API v2.1.
    Gerencia token, paginação e retries básicos.
    """

    def __init__(self):
        self.token       = get_access_token()
        self.base_url    = f"{DOCUSIGN['base_url']}/v2.1/accounts/{DOCUSIGN['account_id']}"
        self.session     = requests.Session()
        self.session.headers.update({
            "Authorization": f"Bearer {self.token}",
            "Content-Type":  "application/json",
        })

    def _get(self, path: str, params: dict = None) -> dict:
        """Executa GET com tratamento de erro."""
        url = f"{self.base_url}{path}"
        resp = self.session.get(url, params=params, timeout=30)

        if resp.status_code == 401:
            # Token expirado — renova e tenta uma vez mais
            self.token = get_access_token()
            self.session.headers["Authorization"] = f"Bearer {self.token}"
            resp = self.session.get(url, params=params, timeout=30)

        resp.raise_for_status()
        return resp.json()

    # ── Envelopes ─────────────────────────────────────────────────────────────

    def list_envelopes(self, from_date: datetime, status: str = "any") -> list[dict]:
        """
        Retorna todos os envelopes alterados desde `from_date`.
        Percorre todas as páginas automaticamente.
        """
        from_date_str = from_date.strftime("%Y-%m-%dT%H:%M:%SZ")
        envelopes = []
        start = 0
        count = 100

        while True:
            data = self._get("/envelopes", params={
                "from_date":     from_date_str,
                "status":        status,
                "count":         count,
                "start_position": start,
                "include":       "recipients",
            })

            batch = data.get("envelopes", [])
            envelopes.extend(batch)

            total = int(data.get("totalSetSize", 0))
            start += count
            if start >= total:
                break

        return envelopes

    def get_envelope(self, envelope_id: str) -> dict:
        """Retorna detalhes completos de um envelope."""
        return self._get(f"/envelopes/{envelope_id}")

    def get_recipients(self, envelope_id: str) -> dict:
        """Retorna todos os destinatários de um envelope."""
        return self._get(f"/envelopes/{envelope_id}/recipients")
