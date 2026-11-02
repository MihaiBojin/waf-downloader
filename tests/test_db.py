import psycopg
import pytest

from waf_logs.db import Database


class FakeConn:
    def __init__(self, closed: bool = False):
        self.closed = closed
        self.rollbacks = 0

    def rollback(self):
        if self.closed:
            raise psycopg.OperationalError("the connection is lost")
        self.rollbacks += 1


class FakePool:
    def __init__(self, conns):
        self.conns = list(conns)
        self.returned = []

    def getconn(self):
        return self.conns.pop(0)

    def putconn(self, conn):
        self.returned.append(conn)


def _db(pool: FakePool) -> Database:
    db = Database.__new__(Database)
    db.connection_pool = None
    db.pool = lambda: pool  # type: ignore[method-assign]
    return db


@pytest.fixture(autouse=True)
def no_sleep(monkeypatch):
    monkeypatch.setattr("waf_logs.db.time.sleep", lambda _: None)


def test_retries_on_a_fresh_connection_after_connection_loss():
    dead, healthy = FakeConn(closed=True), FakeConn()
    pool = FakePool([dead, healthy])
    seen = []

    def func(conn):
        seen.append(conn)
        if conn is dead:
            raise psycopg.OperationalError("terminating connection")
        return "ok"

    assert _db(pool).pooled_exec(func) == "ok"
    assert seen == [dead, healthy]
    assert pool.returned == [dead, healthy]


def test_raises_original_error_when_attempts_run_out():
    pool = FakePool([FakeConn(closed=True) for _ in range(3)])

    def func(conn):
        raise psycopg.OperationalError("terminating connection")

    with pytest.raises(psycopg.OperationalError, match="terminating connection"):
        _db(pool).pooled_exec(func)
    assert len(pool.returned) == 3


def test_other_errors_roll_back_and_are_not_retried():
    conn = FakeConn()
    pool = FakePool([conn])

    def func(_):
        raise ValueError("boom")

    with pytest.raises(ValueError):
        _db(pool).pooled_exec(func)
    assert conn.rollbacks == 1
    assert pool.returned == [conn]
