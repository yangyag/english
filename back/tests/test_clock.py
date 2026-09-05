from datetime import datetime, timezone, date
from app import clock


def test_seoul_day_boundary(monkeypatch):
    class FrozenDatetime:
        instant = datetime(2026, 8, 31, 14, 59, 59, tzinfo=timezone.utc)
        @classmethod
        def now(cls, tz):
            return cls.instant.astimezone(tz)
    monkeypatch.setattr(clock, 'datetime', FrozenDatetime)
    assert clock.get_today() == date(2026, 8, 31)
    FrozenDatetime.instant = datetime(2026, 8, 31, 15, tzinfo=timezone.utc)
    assert clock.get_today() == date(2026, 9, 1)
