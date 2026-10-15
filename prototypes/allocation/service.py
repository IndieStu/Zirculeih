"""P1.5 experiment, not a production booking engine or Django model API.

Callers provide independent PostgreSQL connections. Each public mutation owns its
transaction; unit rows serialize all writers. No HTTP endpoints expose this code.
"""

from datetime import datetime
from uuid import UUID, uuid4

import psycopg
from psycopg.types.range import Range


class Conflict(Exception):
    pass


def lock_units(conn: psycopg.Connection, unit_ids: list[UUID]) -> None:
    # Deterministic order is essential for bundles/pools and concurrent writers.
    for unit_id in sorted(set(unit_ids)):
        if (
            conn.execute("SELECT id FROM unit WHERE id = %s FOR UPDATE", (unit_id,)).fetchone()
            is None
        ):
            raise Conflict("Unknown unit")


def _insert(conn, unit_id: UUID, start: datetime, end: datetime, now: datetime) -> UUID:
    if start < now or end <= start:
        raise Conflict("Invalid reservation interval")
    custody = conn.execute(
        "SELECT expected_return FROM custody WHERE unit_id = %s AND returned_at IS NULL",
        (unit_id,),
    ).fetchone()
    if custody and custody[0] >= start:
        raise Conflict("Return planning does not allow this reservation")
    reservation_id = uuid4()
    conn.execute(
        "INSERT INTO reservation (id, unit_id, during, endangered) VALUES (%s, %s, %s, %s)",
        (reservation_id, unit_id, Range(start, end, "[)"), bool(custody and custody[0] <= now)),
    )
    return reservation_id


def reserve(conn, unit_id: UUID, start: datetime, end: datetime, now: datetime) -> UUID:
    try:
        with conn.transaction():
            lock_units(conn, [unit_id])
            return _insert(conn, unit_id, start, end, now)
    except psycopg.errors.ExclusionViolation as exc:
        raise Conflict("Reservation overlaps") from exc


def reserve_bundle(conn, unit_ids: list[UUID], start, end, now) -> list[UUID]:
    if len(set(unit_ids)) != len(unit_ids):
        raise Conflict("Duplicate component")
    try:
        with conn.transaction():
            lock_units(conn, unit_ids)
            return [_insert(conn, u, start, end, now) for u in sorted(unit_ids)]
    except psycopg.errors.ExclusionViolation as exc:
        raise Conflict("Bundle conflict: nothing reserved") from exc


def reserve_pool(conn, pool_id: UUID, start, end, now) -> UUID:
    with conn.transaction():
        # Freeze the eligible candidate set for this experiment. Production pool
        # reconfiguration must take a pool lock before the same ordered unit locks.
        rows = conn.execute(
            "SELECT id FROM unit WHERE pool_id = %s ORDER BY id", (pool_id,)
        ).fetchall()
        lock_units(conn, [row[0] for row in rows])
        for row in rows:
            try:
                with conn.transaction():  # savepoint: exclusion must not poison outer tx
                    return _insert(conn, row[0], start, end, now)
            except (Conflict, psycopg.errors.ExclusionViolation):
                continue
        raise Conflict("Pool exhausted")


def checkout(conn, reservation_id: UUID, now: datetime) -> UUID:
    with conn.transaction():
        row = conn.execute(
            "SELECT unit_id, during FROM reservation WHERE id = %s AND active",
            (reservation_id,),
        ).fetchone()
        if row is None:
            raise Conflict("Unknown reservation")
        unit_id, during = row
        lock_units(conn, [unit_id])
        # Re-read after locking: other writers may have changed the record.
        row = conn.execute(
            "SELECT during FROM reservation WHERE id = %s AND active", (reservation_id,)
        ).fetchone()
        if row is None or not (row[0].lower <= now < row[0].upper):
            raise Conflict("Outside reservation")
        if conn.execute(
            "SELECT id FROM custody WHERE unit_id = %s AND returned_at IS NULL", (unit_id,)
        ).fetchone():
            raise Conflict("Already physically checked out")
        custody_id = uuid4()
        conn.execute(
            "INSERT INTO custody (id, unit_id, reservation_id, issued_at, expected_return) "
            "VALUES (%s, %s, %s, %s, %s)",
            (custody_id, unit_id, reservation_id, now, row[0].upper),
        )
        return custody_id


def mark_overdue(conn, unit_id: UUID, now: datetime) -> int:
    with conn.transaction():
        lock_units(conn, [unit_id])
        row = conn.execute(
            "SELECT expected_return, reservation_id FROM custody "
            "WHERE unit_id = %s AND returned_at IS NULL AND expected_return <= %s",
            (unit_id, now),
        ).fetchone()
        if not row:
            return 0
        result = conn.execute(
            "UPDATE reservation SET endangered = true WHERE unit_id = %s AND active "
            "AND id <> %s AND upper(during) > %s",
            (unit_id, row[1], row[0]),
        )
        return result.rowcount


def return_unit(conn, unit_id: UUID, now: datetime) -> None:
    with conn.transaction():
        lock_units(conn, [unit_id])
        if (
            conn.execute(
                "UPDATE custody SET returned_at = %s WHERE unit_id = %s AND returned_at IS NULL",
                (now, unit_id),
            ).rowcount
            != 1
        ):
            raise Conflict("No active custody")
