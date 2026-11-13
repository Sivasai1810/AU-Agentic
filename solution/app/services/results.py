"""
results.py - decides what happens to a lead after a call ends (rules R4-R8).

What this file does:
  * handle_result(body) is called for every webhook AND for every call we look up.
  * terminal disposition (interested, not_interested, wrong_number, dnd) -> completed
  * 3 attempts used -> exhausted
  * otherwise -> ready again, with next_time = retry time or the callback time
  * Duplicates are safe: db.save_result ignores a call that was already saved.
"""
from datetime import datetime

from app.database import db
from app.config import campaigns, cfg
from app.rules.scheduling import ready_time

TERMINAL = ["interested", "not_interested", "wrong_number", "dnd"]


def handle_result(body):
    lead = db.get_lead(body["campaign_id"], body["lead_id"])
    if lead["request_id"] != body["request_id"]:
        return  # result of an old call
    status = body["status"]
    disposition = body["disposition"]
    new_state = "ready"
    kind = "retry"
    next_time = lead["next_time"]

    if disposition in TERMINAL:
        new_state = "completed"
    elif lead["attempt_no"] >= campaigns[lead["campaign_id"]]["max_attempts"]:
        new_state = "exhausted"
    else:
        ended_at = datetime.fromisoformat(body["ended_at"])
        callback_at = None
        if body["callback_at"]:
            callback_at = datetime.fromisoformat(body["callback_at"])
        next_time = ready_time(status, disposition, ended_at, callback_at, cfg["retry_policy"]).isoformat()
        if disposition == "callback_requested":
            kind = "callback"
    db.save_result(lead, new_state, kind, next_time, status, disposition)
