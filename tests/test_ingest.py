from datetime import datetime, timezone
from types import SimpleNamespace

from pipeline.ingest import wait_time


def reply(retry_after=None):
    """A stand-in for a response: only the header that wait_time reads."""
    return SimpleNamespace(headers={} if retry_after is None else {"Retry-After": retry_after})


def test_a_number_of_seconds_is_obeyed():
    assert wait_time(reply("3"), attempt=1) == 3.0


def test_no_header_means_a_doubling_wait():
    assert [wait_time(reply(), attempt=n) for n in (1, 2, 3)] == [0.5, 1.0, 2.0]


def test_a_date_means_the_seconds_until_then():
    now = datetime(2026, 11, 24, 8, 0, 0, tzinfo=timezone.utc)
    assert wait_time(reply("Tue, 24 Nov 2026 08:00:10 GMT"), attempt=1, now=now) == 10.0
