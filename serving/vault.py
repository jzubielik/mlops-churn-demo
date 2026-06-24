"""Fetching the service secret from HashiCorp Vault (hvac client).

Principle: the service NEVER hardcodes the secret in code. At startup it asks
Vault for the secret under the KV v2 path ``churn/app`` and reads the
``api_token`` field from it (a token we would use to e.g. authorize /predict calls).

If Vault is UNAVAILABLE (common in dev/demo mode without a container), the client
degrades gracefully: it returns a secret with ``source="fallback"`` instead of
crashing the service. This way `make serve` and `make demo` work without Vault too,
and we demonstrate the full "from Vault" path via `make vault-up && make vault-seed`.

Configuration via env (this is the *address* and *access token*, not the business secret itself):

    VAULT_ADDR   - Vault server address (default http://127.0.0.1:17200)
    VAULT_TOKEN  - authentication token (dev mode: dev-only-token)
    VAULT_KV_MOUNT / VAULT_KV_PATH - secret mount and path (secret / churn/app)

In a real deployment, instead of a static root token you would use AppRole /
Kubernetes auth / Vault Agent with short-lived tokens.
"""

from __future__ import annotations

import os
from dataclasses import dataclass

VAULT_ADDR = os.environ.get("VAULT_ADDR", "http://127.0.0.1:17200")
VAULT_TOKEN = os.environ.get("VAULT_TOKEN", "dev-only-token")

SECRET_MOUNT = os.environ.get("VAULT_KV_MOUNT", "secret")
SECRET_PATH = os.environ.get("VAULT_KV_PATH", "churn/app")

# Fallback value when Vault is unavailable (dev/demo only).
FALLBACK_TOKEN = os.environ.get("CHURN_API_TOKEN", "dev-fallback-token")


@dataclass
class AppSecret:
    """Business secret of the churn service (e.g. an API token)."""

    api_token: str
    source: str  # "vault:..." or "fallback" — for healthcheck/audit

    def masked(self) -> str:
        """Masked representation — safe for logs and /health."""
        if not self.api_token:
            return "<empty>"
        tail = self.api_token[-2:] if len(self.api_token) > 2 else ""
        return f"{'*' * 6}{tail}"


def read_app_secret() -> AppSecret:
    """Reads the secret from Vault KV v2. On ANY error it degrades to the fallback.

    This is the only place in the service that "knows" how to obtain the token.
    """
    try:
        import hvac
    except ImportError:
        return AppSecret(api_token=FALLBACK_TOKEN, source="fallback:no-hvac")

    try:
        client = hvac.Client(url=VAULT_ADDR, token=VAULT_TOKEN)
        if not client.is_authenticated():
            return AppSecret(api_token=FALLBACK_TOKEN, source="fallback:unauthenticated")
        resp = client.secrets.kv.v2.read_secret_version(
            mount_point=SECRET_MOUNT,
            path=SECRET_PATH,
            raise_on_deleted_version=True,
        )
        data = resp["data"]["data"]
        token = data.get("api_token")
        if not token:
            return AppSecret(api_token=FALLBACK_TOKEN, source="fallback:missing-field")
        return AppSecret(
            api_token=token,
            source=f"vault:{VAULT_ADDR}/{SECRET_MOUNT}/{SECRET_PATH}",
        )
    except Exception:  # noqa: BLE001 — Vault down → graceful degradation
        return AppSecret(api_token=FALLBACK_TOKEN, source="fallback:unreachable")
