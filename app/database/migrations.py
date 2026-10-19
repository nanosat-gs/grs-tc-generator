"""Idempotent schema changes, run at boot after create_all.

create_all only creates missing tables; it never touches an existing one. The
status CHECK of `telecommands` grew two values with the uplink slice
(`response_received`, `no_response`), so a database created before that needs
the constraint replaced. This module is the TC Generator's, because the table
is: the TC Scheduler and the grs-uplink only read it or write statuses.

The constraint may exist under two names: `telecommands_status_check` when
the table came from resources/database/schema.sql (inline CHECK), or
`valid_status` when it came from create_all (the model). Both are dropped and
`valid_status` is recreated — only if the current definition lacks a status.
"""

from __future__ import annotations

import logging

from sqlalchemy import text
from sqlalchemy.engine import Engine

from app.services.uplink_catalog import STATUSES

logger = logging.getLogger(__name__)

CONSTRAINT_NAMES = ("telecommands_status_check", "valid_status")


def status_check_sql() -> str:
    return "status IN (" + ", ".join(f"'{status}'" for status in STATUSES) + ")"


def ensure_status_constraint(engine: Engine) -> bool:
    """:return: True if the constraint was replaced."""
    with engine.begin() as connection:
        if connection.execute(text("SELECT to_regclass('public.telecommands')")).scalar() is None:
            return False
        definitions = connection.execute(text("""
            SELECT pg_get_constraintdef(c.oid)
            FROM pg_constraint c JOIN pg_class t ON t.oid = c.conrelid
            WHERE t.relname = 'telecommands' AND c.contype = 'c' AND c.conname = ANY(:names)
        """), {"names": list(CONSTRAINT_NAMES)}).scalars().all()
        if definitions and all(f"'{status}'" in definitions[0] for status in STATUSES) \
                and len(definitions) == 1:
            return False

        for name in CONSTRAINT_NAMES:
            connection.execute(text(f"ALTER TABLE telecommands DROP CONSTRAINT IF EXISTS {name}"))
        connection.execute(text(
            f"ALTER TABLE telecommands ADD CONSTRAINT valid_status CHECK ({status_check_sql()})"))
    logger.info("telecommands.status CHECK updated: %s", ", ".join(STATUSES))
    return True
