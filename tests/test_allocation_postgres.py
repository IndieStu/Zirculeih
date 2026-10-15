from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime, timedelta
from threading import Barrier
from uuid import uuid4

import psycopg
import pytest
from psycopg.types.range import Range

from prototypes.allocation import service

pytestmark = pytest.mark.postgres
NOW = datetime(2026, 10, 14, 10, tzinfo=UTC)


def seed(factory, count=1):
    pool = uuid4()
    units = [uuid4() for _ in range(count)]
    with factory() as conn:
        for unit in units:
            conn.execute("INSERT INTO unit VALUES (%s, %s)", (unit, pool))
    return pool, units


def parallel(factory, count, operation):
    barrier = Barrier(count)

    def attempt(index):
        with factory() as conn:
            barrier.wait(timeout=10)
            try:
                return operation(conn, index)
            except service.Conflict:
                return None

    with ThreadPoolExecutor(max_workers=count) as executor:
        return list(executor.map(attempt, range(count)))


def test_twenty_same_unit_requests_have_exactly_one_winner(pg_factory):
    _, (unit,) = seed(pg_factory)
    results = parallel(
        pg_factory,
        20,
        lambda c, _: service.reserve(
            c, unit, NOW + timedelta(days=1), NOW + timedelta(days=2), NOW
        ),
    )
    assert sum(x is not None for x in results) == 1
    with pg_factory() as conn:
        assert conn.execute("SELECT count(*) FROM reservation").fetchone()[0] == 1


def test_pool_five_units_six_parallel_requests(pg_factory):
    pool, _ = seed(pg_factory, 5)
    results = parallel(
        pg_factory,
        6,
        lambda c, _: service.reserve_pool(
            c, pool, NOW + timedelta(days=1), NOW + timedelta(days=2), NOW
        ),
    )
    assert sum(x is not None for x in results) == 5
    with pg_factory() as conn:
        assert conn.execute("SELECT count(DISTINCT unit_id) FROM reservation").fetchone()[0] == 5


def test_adjacent_intervals_and_direct_database_exclusion(pg_factory):
    _, (unit,) = seed(pg_factory)
    with pg_factory() as conn:
        service.reserve(conn, unit, NOW, NOW + timedelta(hours=1), NOW)
        service.reserve(conn, unit, NOW + timedelta(hours=1), NOW + timedelta(hours=2), NOW)
        # Direct SQL proves database exclusion even if service validation is bypassed.
        with pytest.raises(psycopg.errors.ExclusionViolation), conn.transaction():
            conn.execute(
                "INSERT INTO reservation (id, unit_id, during) VALUES (%s,%s,%s)",
                (uuid4(), unit, Range(NOW, NOW + timedelta(minutes=30), "[)")),
            )
        assert conn.execute("SELECT count(*) FROM reservation").fetchone()[0] == 2


def open_loan(factory):
    _, (unit,) = seed(factory)
    with factory() as conn:
        first = service.reserve(conn, unit, NOW, NOW + timedelta(days=2), NOW)
        custody = service.checkout(conn, first, NOW)
    return unit, custody


def test_open_loan_allows_future_binding_reservation(pg_factory):
    unit, _ = open_loan(pg_factory)
    with pg_factory() as conn:
        following = service.reserve(
            conn, unit, NOW + timedelta(days=7), NOW + timedelta(days=8), NOW
        )
        assert following
        assert conn.execute("SELECT returned_at FROM custody").fetchone()[0] is None
        with pytest.raises(service.Conflict):
            service.reserve(conn, unit, NOW + timedelta(days=1), NOW + timedelta(days=3), NOW)


def test_overdue_keeps_following_booking_but_prevents_second_checkout(pg_factory):
    unit, _ = open_loan(pg_factory)
    start = NOW + timedelta(days=7)
    with pg_factory() as conn:
        following = service.reserve(conn, unit, start, start + timedelta(days=1), NOW)
        assert service.mark_overdue(conn, unit, start) == 1
        assert conn.execute(
            "SELECT active, endangered FROM reservation WHERE id=%s", (following,)
        ).fetchone() == (True, True)
        with pytest.raises(service.Conflict):
            service.checkout(conn, following, start)
        later = service.reserve(
            conn, unit, start + timedelta(days=3), start + timedelta(days=4), start
        )
        assert (
            conn.execute("SELECT endangered FROM reservation WHERE id=%s", (later,)).fetchone()[0]
            is True
        )
        # Actual return, not due date, ends custody. Checkout is then possible.
        service.return_unit(conn, unit, start)
        service.checkout(conn, following, start)
        assert (
            conn.execute("SELECT count(*) FROM custody WHERE returned_at IS NULL").fetchone()[0]
            == 1
        )


def test_two_parallel_checkouts_have_one_physical_winner(pg_factory):
    _, (unit,) = seed(pg_factory)
    with pg_factory() as conn:
        booking = service.reserve(conn, unit, NOW, NOW + timedelta(hours=2), NOW)
    results = parallel(pg_factory, 2, lambda c, _: service.checkout(c, booking, NOW))
    assert sum(x is not None for x in results) == 1


def test_unique_custody_constraint_cannot_be_bypassed(pg_factory):
    unit, _ = open_loan(pg_factory)
    with pg_factory() as conn:
        booking = conn.execute("SELECT id FROM reservation").fetchone()[0]
        with pytest.raises(psycopg.errors.UniqueViolation), conn.transaction():
            conn.execute(
                "INSERT INTO custody VALUES (%s,%s,%s,%s,%s,NULL)",
                (uuid4(), unit, booking, NOW, NOW + timedelta(days=2)),
            )


def test_competing_bundles_rollback_all_components(pg_factory):
    _, units = seed(pg_factory, 3)
    start, end = NOW + timedelta(days=1), NOW + timedelta(days=2)
    results = parallel(
        pg_factory, 2, lambda c, i: service.reserve_bundle(c, [units[i], units[2]], start, end, NOW)
    )
    assert sum(x is not None for x in results) == 1
    with pg_factory() as conn:
        assert conn.execute("SELECT count(*) FROM reservation").fetchone()[0] == 2


def test_checkout_and_future_reservation_can_commit_together(pg_factory):
    _, (unit,) = seed(pg_factory)
    with pg_factory() as conn:
        booking = service.reserve(conn, unit, NOW, NOW + timedelta(days=2), NOW)

    def operation(conn, i):
        if i == 0:
            return service.checkout(conn, booking, NOW)
        return service.reserve(conn, unit, NOW + timedelta(days=7), NOW + timedelta(days=8), NOW)

    assert all(parallel(pg_factory, 2, operation))
