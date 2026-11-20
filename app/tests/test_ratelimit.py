from datetime import UTC, datetime, timedelta

import pytest

from app.db import Database
from app.ratelimit import BASE_LOCK, MAX_FAILURES, RateLimiter


class Clock:
    def __init__(self):
        self.t = datetime(2026, 11, 20, 12, 0, tzinfo=UTC)

    def __call__(self):
        return self.t

    def advance(self, **kwargs):
        self.t += timedelta(**kwargs)


@pytest.fixture()
def env():
    clock = Clock()
    db = Database(":memory:")
    return RateLimiter(db, clock), clock, db


def _fail(limiter, client="1.1.1.1", times=MAX_FAILURES):
    return [limiter.register_failure(client) for _ in range(times)]


def test_four_failures_do_not_lock_the_fifth_does(env):
    limiter, _, _ = env
    events = _fail(limiter, times=MAX_FAILURES)
    assert all(e is None for e in events[:-1]) and events[-1] is not None
    assert limiter.retry_after("1.1.1.1") == int(BASE_LOCK.total_seconds())


def test_lock_expires_and_then_doubles_on_reincidence(env):
    limiter, clock, _ = env
    _fail(limiter)
    clock.advance(minutes=15, seconds=1)
    assert limiter.retry_after("1.1.1.1") == 0
    second = _fail(limiter)[-1]
    assert second.level == 1
    assert limiter.retry_after("1.1.1.1") == int(
        (BASE_LOCK * 2).total_seconds()
    )  # 30 min


def test_lock_doubles_each_time_up_to_the_daily_cap(env):
    limiter, clock, _ = env
    durations = []
    for _ in range(8):
        _fail(limiter)
        durations.append(limiter.retry_after("1.1.1.1"))
        clock.advance(seconds=durations[-1] + 1)  # espera a que venza y reincide
    minutes = [d // 60 for d in durations]
    assert minutes == [15, 30, 60, 120, 240, 480, 960, 1440]  # ... tope: 24 h


def test_level_resets_after_a_day_without_failures(env):
    limiter, clock, _ = env
    _fail(limiter)
    clock.advance(hours=25)
    assert _fail(limiter)[-1].level == 0  # vuelve a empezar en 15 minutos


def test_failures_outside_the_window_are_forgotten(env):
    limiter, clock, _ = env
    _fail(limiter, times=MAX_FAILURES - 1)
    clock.advance(minutes=16)
    assert (
        limiter.register_failure("1.1.1.1") is None
    )  # cuenta como el primero de nuevo
    assert limiter.retry_after("1.1.1.1") == 0


def test_success_clears_the_failure_count(env):
    limiter, _, _ = env
    _fail(limiter, times=MAX_FAILURES - 1)
    limiter.register_success("1.1.1.1")
    assert _fail(limiter, times=MAX_FAILURES - 1)[-1] is None


def test_clients_are_independent(env):
    limiter, _, _ = env
    _fail(limiter, "1.1.1.1")
    assert limiter.retry_after("2.2.2.2") == 0


def test_lock_survives_a_restart(env):
    limiter, clock, db = env
    _fail(limiter)
    restarted = RateLimiter(db, clock)  # "servidor reiniciado": misma base
    assert restarted.retry_after("1.1.1.1") > 0


def test_daily_attempts_are_far_below_the_old_policy(env):
    """Con 5 fallos / 5 min un atacante hacia ~1 440 intentos al dia por direccion."""
    limiter, clock, _ = env
    attempts = 0
    for _ in range(24 * 60):  # un minuto por paso durante un dia
        if limiter.retry_after("8.8.8.8") == 0:
            limiter.register_failure("8.8.8.8")
            attempts += 1
        clock.advance(minutes=1)
    assert attempts < 60
