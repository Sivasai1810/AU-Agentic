"""
test_scheduling.py - tests for scheduling.py using fake times (no mock provider, no waiting).
Run:  cd solution && python -m pytest
Covers: window maths (R1), next eligible time (R5, R6), priority order (R6).
"""
from datetime import datetime, timedelta

from app.rules.scheduling import IST, can_start, in_window, ready_time, sort_key

REGULATORY = {"start": "09:00", "end": "21:00"}
WINDOW = {"start": "10:00", "end": "19:00", "days": ["mon", "tue", "wed", "thu", "fri", "sat"]}
POLICY = {"no_answer_minutes": 60, "busy_minutes": 60, "failed_minutes": 15}


def at(day, hour, minute=0):  # 12 Nov 2026 is a Thursday, 15 Nov is a Sunday
    return datetime(2026, 11, day, hour, minute, tzinfo=IST)


def test_inside_window():
    assert can_start(at(12, 11), WINDOW, REGULATORY)


def test_start_is_included_end_is_not():
    assert can_start(at(12, 10, 0), WINDOW, REGULATORY)
    assert not can_start(at(12, 9, 59), WINDOW, REGULATORY)
    assert not can_start(at(12, 19, 0), WINDOW, REGULATORY)


def test_stops_just_before_end():
    assert not can_start(at(12, 18, 59) + timedelta(seconds=30), WINDOW, REGULATORY)


def test_bigger_margin_stops_earlier():
    assert can_start(at(12, 18, 50), WINDOW, REGULATORY, margin=120)
    assert not can_start(at(12, 18, 50), WINDOW, REGULATORY, margin=1200)


def test_wrong_day():
    assert not can_start(at(15, 11), WINDOW, REGULATORY)  # Sunday


def test_regulatory_window_wins():
    late = {"start": "10:00", "end": "22:00", "days": WINDOW["days"]}
    assert not can_start(at(12, 21, 30), late, REGULATORY)


def test_works_with_utc_time():
    utc_time = at(12, 11).astimezone(tz=None)
    assert in_window(utc_time, "10:00", "19:00")


def test_retry_waits():
    ended = at(12, 12)
    assert ready_time("no_answer", None, ended, None, POLICY) == ended + timedelta(minutes=60)
    assert ready_time("busy", None, ended, None, POLICY) == ended + timedelta(minutes=60)
    assert ready_time("failed", None, ended, None, POLICY) == ended + timedelta(minutes=15)


def test_callback_uses_callback_time():
    assert ready_time("completed", "callback_requested", at(12, 12), at(12, 15), POLICY) == at(12, 15)


def test_priority_callback_then_retry_then_fresh():
    leads = [("fresh", at(12, 9)), ("retry", at(12, 10)), ("callback", at(12, 11)), ("retry", at(12, 8))]
    leads.sort(key=lambda lead: sort_key(*lead))
    assert [kind for kind, _ in leads] == ["callback", "retry", "retry", "fresh"]
    assert leads[1][1] == at(12, 8)  # older retry first
