"""OAuth token refresh for Lakebase Provisioned connections.

Tokens expire after ~1 hour. The COMPASS app's FastAPI backend holds long-lived
SQLAlchemy pools, so we proactively rotate before expiry and rebuild auth.

Usage (FastAPI startup):

    from app.backend.lakebase_token import LakebaseTokenManager, make_engine

    manager = LakebaseTokenManager(instance="compass-lakebase-prov")
    engine = make_engine(
        host=os.environ["COMPASS_LAKEBASE_HOST"],
        database=os.environ.get("COMPASS_LAKEBASE_DB", "databricks_postgres"),
        user=os.environ["COMPASS_LAKEBASE_USER"],
        manager=manager,
    )

CLI smoke test:

    DATABRICKS_CONFIG_PROFILE=fe-vm-classic-stable-1zia5t-kp \
        python -m app.backend.lakebase_token
"""

from __future__ import annotations

import os
import threading
import time
import uuid
from dataclasses import dataclass
from typing import Optional

from databricks.sdk import WorkspaceClient

REFRESH_BUFFER_SECONDS = 300
DEFAULT_TTL_SECONDS = 3600


@dataclass
class _CachedToken:
    value: str
    expires_at: float


class LakebaseTokenManager:
    """Thread-safe cache + rotation for a Lakebase Provisioned instance's OAuth token."""

    def __init__(
        self,
        instance: str,
        workspace_client: Optional[WorkspaceClient] = None,
        ttl_seconds: int = DEFAULT_TTL_SECONDS,
    ):
        self.instance = instance
        self._w = workspace_client or WorkspaceClient()
        self._ttl = ttl_seconds
        self._lock = threading.Lock()
        self._cached: Optional[_CachedToken] = None

    def get_token(self) -> str:
        with self._lock:
            now = time.time()
            if self._cached and self._cached.expires_at - now > REFRESH_BUFFER_SECONDS:
                return self._cached.value
            cred = self._w.database.generate_database_credential(
                request_id=str(uuid.uuid4()),
                instance_names=[self.instance],
            )
            self._cached = _CachedToken(value=cred.token, expires_at=now + self._ttl)
            return self._cached.value

    def invalidate(self) -> None:
        """Force a refresh on the next get_token() call (e.g. after a 401)."""
        with self._lock:
            self._cached = None


def make_engine(
    host: str,
    database: str,
    user: str,
    manager: LakebaseTokenManager,
    pool_size: int = 5,
    max_overflow: int = 5,
):
    """Build a SQLAlchemy engine that fetches a fresh token per new connection."""
    from sqlalchemy import create_engine
    from sqlalchemy.engine.url import URL

    url = URL.create(
        drivername="postgresql+psycopg",
        username=user,
        host=host,
        database=database,
    )

    def _on_do_connect(dialect, conn_rec, cargs, cparams):
        cparams["password"] = manager.get_token()
        cparams["sslmode"] = "require"

    engine = create_engine(
        url,
        pool_pre_ping=True,
        pool_size=pool_size,
        max_overflow=max_overflow,
    )
    from sqlalchemy import event
    event.listen(engine, "do_connect", _on_do_connect)
    return engine


if __name__ == "__main__":
    instance = os.environ.get("COMPASS_LAKEBASE_INSTANCE", "compass-lakebase-prov")
    host = os.environ.get(
        "COMPASS_LAKEBASE_HOST",
        "ep-raspy-credit-d2yhs2ud.database.us-east-1.cloud.databricks.com",
    )
    database = os.environ.get("COMPASS_LAKEBASE_DB", "databricks_postgres")
    user = os.environ.get("COMPASS_LAKEBASE_USER", "kaustav.paul@databricks.com")

    manager = LakebaseTokenManager(instance=instance)
    t1 = manager.get_token()
    t2 = manager.get_token()
    assert t1 == t2, "Cached token must be reused within the refresh window."
    print(f"[ok] token length={len(t1)}, cached for ~{manager._ttl}s")

    engine = make_engine(host=host, database=database, user=user, manager=manager)
    with engine.connect() as conn:
        from sqlalchemy import text
        result = conn.execute(text("SELECT current_user, count(*) FROM compass.app_user")).one()
        print(f"[ok] current_user={result[0]} app_user_rows={result[1]}")
    print("[ok] engine round-trip succeeded; token rotation is wired up.")
