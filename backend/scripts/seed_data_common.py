from __future__ import annotations

import base64
import hashlib
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import UUID, uuid5

from sqlalchemy import MetaData, create_engine, inspect, text
from sqlalchemy.engine import Engine, make_url

SEED = 20261022
NAMESPACE = UUID("93f7e985-20b0-4b13-88f2-f14bf6aedf5a")
REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
BACKEND_ROOT = REPOSITORY_ROOT / "backend"
GENERATOR_VERSION = "1.0"
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))


def stable_id(entity: str, *parts: object) -> UUID:
    name = ":".join([str(SEED), entity, *(str(part) for part in parts)])
    return uuid5(NAMESPACE, name)


def canonical_json(value: Any) -> bytes:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")


def sha256(value: bytes) -> bytes:
    return hashlib.sha256(value).digest()


def to_json_value(value: Any) -> Any:
    if isinstance(value, UUID):
        return str(value)
    if isinstance(value, bytes):
        return {"$base64": base64.b64encode(value).decode("ascii")}
    if isinstance(value, datetime):
        return value.astimezone(timezone.utc).isoformat(timespec="microseconds")
    if isinstance(value, dict):
        return {key: to_json_value(value[key]) for key in sorted(value)}
    if isinstance(value, (tuple, list)):
        return [to_json_value(item) for item in value]
    if hasattr(value, "as_tuple") and value.__class__.__name__ == "Decimal":
        return format(value, "f")
    return value


def database_url() -> str:
    url = os.environ.get("SYNTHETIC_DATABASE_URL")
    if not url:
        raise RuntimeError(
            "Set SYNTHETIC_DATABASE_URL to an explicitly designated synthetic database."
        )
    parsed = make_url(url)
    if parsed.get_backend_name() != "postgresql":
        raise RuntimeError("Synthetic data generation requires PostgreSQL.")
    if not parsed.database:
        raise RuntimeError("SYNTHETIC_DATABASE_URL must include a database name.")
    return url


def make_engine() -> Engine:
    return create_engine(database_url(), pool_pre_ping=True, future=True)


def reset_database(engine: Engine) -> None:
    database_name = make_url(database_url()).database or ""
    if "synthetic" not in database_name.casefold():
        raise RuntimeError(
            "Refusing reset: the database name must contain 'synthetic'. "
            "Use a dedicated database such as credential_synthetic."
        )
    if os.environ.get("CONFIRM_SYNTHETIC_DATABASE_RESET") != "YES":
        raise RuntimeError(
            "Refusing reset: set CONFIRM_SYNTHETIC_DATABASE_RESET=YES only "
            "after confirming this is a disposable synthetic database."
        )

    from app.database.base import Base
    import app.models  # noqa: F401

    Base.metadata.drop_all(engine)
    with engine.begin() as connection:
        connection.execute(text("DROP TABLE IF EXISTS alembic_version"))

    from alembic import command
    from alembic.config import Config

    previous_url = os.environ.get("DATABASE_URL")
    previous_secret = os.environ.get("SECRET_KEY")
    os.environ["DATABASE_URL"] = database_url()
    os.environ.setdefault("SECRET_KEY", "synthetic-database-reset-only")
    try:
        backend_dir = REPOSITORY_ROOT / "backend"
        config = Config(str(backend_dir / "alembic.ini"))
        config.set_main_option("script_location", str(backend_dir / "migrations"))
        command.upgrade(config, "head")
    finally:
        if previous_url is None:
            os.environ.pop("DATABASE_URL", None)
        else:
            os.environ["DATABASE_URL"] = previous_url
        if previous_secret is None:
            os.environ.pop("SECRET_KEY", None)
        else:
            os.environ["SECRET_KEY"] = previous_secret


def ensure_database_empty(engine: Engine) -> None:
    from app.database.base import Base
    import app.models  # noqa: F401

    inspector = inspect(engine)
    expected_tables = set(Base.metadata.tables)
    existing_tables = set(inspector.get_table_names())
    missing = expected_tables - existing_tables
    if missing:
        raise RuntimeError(
            "Database schema is not migrated. Apply `alembic upgrade head` first; "
            f"missing tables: {', '.join(sorted(missing))}."
        )
    with engine.connect() as connection:
        for name in sorted(expected_tables):
            table = Base.metadata.tables[name]
            if connection.execute(table.select().limit(1)).first() is not None:
                raise RuntimeError(
                    f"Table {name!r} is not empty. Use the guarded reset option "
                    "only for a dedicated synthetic database."
                )


def model_metadata() -> MetaData:
    from app.database.base import Base
    import app.models  # noqa: F401

    return Base.metadata


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()
