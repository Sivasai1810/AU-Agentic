"""
test_results.py - tests for the lead state changes (results.py + db.py) using a temporary database.
Run:  cd solution && python -m pytest
Covers: duplicate webhook, exhausted after 3 attempts, DND blocking, callback priority.
"""
import pytest

from app.database import db
from app.services import results

BODY = {"campaign_id": "c_acme_renewals", "lead_id": "ren_0001", "request_id": "r1", "status": "no_answer",
        "disposition": None, "callback_at": None, "ended_at": "2026-11-12T12:00:00+05:30"}


@pytest.fixture(autouse=True)
def fresh_db(tmp_path, monkeypatch):
    monkeypatch.setattr(db, "DB_FILE", str(tmp_path / "test.db"))
    db.create_table()
    db.add_lead("c_acme_renewals", "ren_0001", "+911", "acme_insurance", "2026-11-12T10:00:00+05:30")
    db.add_lead("c_acme_feedback", "fb_0001", "+911", "acme_insurance", "2026-11-12T10:00:00+05:30")


def start_call(attempts_before=0):
    db.run("UPDATE leads SET attempts=? WHERE lead_id='ren_0001'", (attempts_before,))
    lead = db.get_lead("c_acme_renewals", "ren_0001")
    db.mark_dialing(lead, "r1")


def state():
    return db.get_lead("c_acme_renewals", "ren_0001")


def test_no_answer_goes_back_to_ready_in_60_minutes():
    start_call()
    results.handle_result(BODY)
    assert state()["state"] == "ready"
    assert state()["next_time"].startswith("2026-11-12T13:00")


def test_duplicate_webhook_changes_nothing():
    start_call()
    results.handle_result(BODY)
    db.run("UPDATE leads SET next_time='x'")
    results.handle_result(BODY)
    assert state()["next_time"] == "x"


def test_third_attempt_without_terminal_is_exhausted():
    start_call(attempts_before=2)
    results.handle_result(BODY)
    assert state()["state"] == "exhausted"
    assert state()["attempts"] == 3


def test_callback_becomes_callback_kind():
    start_call()
    body = dict(BODY, status="completed", disposition="callback_requested", callback_at="2026-11-12T15:00:00+05:30")
    results.handle_result(body)
    assert state()["kind"] == "callback"
    assert state()["next_time"].startswith("2026-11-12T15:00")


def test_dnd_completes_lead_and_blocks_same_phone():
    start_call()
    results.handle_result(dict(BODY, status="completed", disposition="dnd"))
    assert state()["state"] == "completed"
    assert db.get_lead("c_acme_feedback", "fb_0001")["state"] == "dnd_blocked"
