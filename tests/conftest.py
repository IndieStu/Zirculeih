from pathlib import Path
from uuid import uuid4

import psycopg
import pytest
from django.db import connection
from psycopg import sql


@pytest.fixture
def pg_factory(transactional_db):
    """One real, independently committed connection per participant."""
    assert connection.vendor == "postgresql", "PostgreSQL required; no SQLite substitute"
    db = connection.settings_dict
    params = dict(
        dbname=db["NAME"],
        user=db["USER"],
        password=db["PASSWORD"],
        host=db["HOST"],
        port=db["PORT"],
        connect_timeout=5,
    )
    schema = "prototype_" + uuid4().hex
    with psycopg.connect(**params, autocommit=True) as admin:
        admin.execute("CREATE EXTENSION IF NOT EXISTS btree_gist")
        admin.execute(sql.SQL("CREATE SCHEMA {}").format(sql.Identifier(schema)))
        admin.execute(sql.SQL("SET search_path TO {}, public").format(sql.Identifier(schema)))
        admin.execute(Path("prototypes/allocation/schema.sql").read_text())
    opened = []

    def factory():
        conn = psycopg.connect(
            **params,
            autocommit=True,
            options=f"-c search_path={schema},public -c statement_timeout=15000",
        )
        opened.append(conn)
        return conn

    yield factory
    for conn in opened:
        conn.close()
    with psycopg.connect(**params, autocommit=True) as admin:
        admin.execute(sql.SQL("DROP SCHEMA {} CASCADE").format(sql.Identifier(schema)))
