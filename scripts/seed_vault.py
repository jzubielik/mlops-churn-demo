"""Writes the churn service secret to Vault KV v2 under the path churn/app.

This is "seeding" — a one-time upload of the secret to Vault. In the real world
this is done by an operator/platform (or a pipeline with separate permissions),
not the service itself.

Run (after `make vault-up`):
    python scripts/seed_vault.py
or:
    make vault-seed

Configuration via env: VAULT_ADDR, VAULT_TOKEN (defaults to dev mode :17200).
"""

from __future__ import annotations

import os
import secrets as _secrets
import sys

VAULT_ADDR = os.environ.get("VAULT_ADDR", "http://127.0.0.1:17200")
VAULT_TOKEN = os.environ.get("VAULT_TOKEN", "dev-only-token")
MOUNT = os.environ.get("VAULT_KV_MOUNT", "secret")
PATH = os.environ.get("VAULT_KV_PATH", "churn/app")


def main() -> int:
    try:
        import hvac
    except ImportError:
        print("Missing hvac package. Run: make install", file=sys.stderr)
        return 1

    client = hvac.Client(url=VAULT_ADDR, token=VAULT_TOKEN)
    if not client.is_authenticated():
        print(
            f"Cannot authenticate with Vault ({VAULT_ADDR}).\n"
            "Is Vault running? Run: make vault-up",
            file=sys.stderr,
        )
        return 1

    # Token generated randomly — the secret is never hardcoded in the repo.
    # Can be overridden via the CHURN_API_TOKEN env (e.g. in a pipeline).
    token = os.environ.get("CHURN_API_TOKEN") or _secrets.token_urlsafe(24)

    client.secrets.kv.v2.create_or_update_secret(
        mount_point=MOUNT,
        path=PATH,
        secret={"api_token": token, "owner": "churn-serving"},
    )

    masked = "*" * 6 + token[-2:]
    print(f"OK: secret written to Vault -> {MOUNT}/{PATH}")
    print(f"    api_token={masked}  (the full value stays in Vault)")
    print("Now start the service: make serve  (it fetches the secret at startup)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
