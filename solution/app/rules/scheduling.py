"""
scheduling.py - pure time/ordering rules for the dispatcher (no network, no database).

What this file does:
  * in_window / can_start : is a call allowed to START right now? (R1)
  * ready_time            : when may a lead be called again after a call ends? (R5, R6)
  * sort_key              : who goes first? callbacks, then retries, then fresh leads (R6)
Every function takes "now" as an argument, so tests can use a fake clock.
"""
from datetime import datetime, timedelta, timezone

IST = timezone(timedelta(hours=5, minutes=30))
DAYS = ["mon", "tue", "wed", "thu", "fri", "sat", "sun"]
ORDER = {"callback": 0, "retry": 1, "fresh": 2}


def in_window(now, start, end, days=None, margin=120):
    """True if now is in [start, end). We stop `margin` seconds early to be safe."""
    t = now.astimezone(IST)
    if days is not None and DAYS[t.weekday()] not in days:
        return False
    seconds = t.hour * 3600 + t.minute * 60 + t.second
    start_h, start_m = start.split(":")
    end_h, end_m = end.split(":")
    start_s = int(start_h) * 3600 + int(start_m) * 60
    end_s = int(end_h) * 3600 + int(end_m) * 60
    return start_s <= seconds < end_s - margin


def can_start(now, window, regulatory, margin=120):
    """Must be inside the campaign window AND the 09:00-21:00 regulatory window."""
    in_campaign = in_window(now, window["start"], window["end"], window["days"], margin)
    in_law = in_window(now, regulatory["start"], regulatory["end"], None, margin)
    return in_campaign and in_law


def ready_time(status, disposition, ended_at, callback_at, policy):
    """Earliest time the lead may be called again after a call ended."""
    if disposition == "callback_requested":
        return callback_at
    return ended_at + timedelta(minutes=policy[status + "_minutes"])


def sort_key(kind, when):
    """Smaller key = dialled first. Callbacks, then retries, then fresh; oldest first."""
    return (ORDER[kind], when)
