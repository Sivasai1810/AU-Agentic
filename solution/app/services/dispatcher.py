"""
dispatcher.py - the main loop: decide who to call, call them, and recover from problems.

What this file does:
  * pick_leads : chooses ready leads that obey window, tenant limit, one-call-per-phone and
                 priority (callbacks > retries > fresh). Saves each as 'dialing' BEFORE calling.
  * dial       : sends the call. 503 -> try later. 504 / network error -> ask the provider.
  * check_stuck: asks the provider about calls with no result yet (lost webhook, crash).
  * run        : repeats all of this until every lead is finished.
"""
import time
from collections import Counter
from datetime import datetime

from app.database import db
from app.services import provider, results
from app.config import campaigns, cfg, tenant_limit
from app.rules.scheduling import can_start, sort_key


def lead_order(lead):
    return sort_key(lead["kind"], datetime.fromisoformat(lead["next_time"]))


def window_ok(lead, now):
    # The provider can answer slowly, so stop dialling early: 2 real seconds before the window ends
    margin = max(120, 2 * provider.clock["speed"])
    return can_start(now, campaigns[lead["campaign_id"]]["window"], cfg["regulatory_window"], margin)


def pick_leads():
    now = provider.sim_now()
    used = Counter()  # active calls per tenant
    busy_phones = []
    for row in db.busy_leads():
        used[row["tenant_id"]] += 1
        busy_phones.append(row["phone"])

    due = []
    for lead in db.ready_leads():
        if datetime.fromisoformat(lead["next_time"]) <= now:
            due.append(lead)
    due.sort(key=lead_order)

    chosen = []
    for lead in due:
        if not window_ok(lead, now):
            continue
        if used[lead["tenant_id"]] >= tenant_limit[lead["tenant_id"]]:
            continue
        if lead["phone"] in busy_phones:
            continue
        request_id = lead["campaign_id"] + "-" + lead["lead_id"] + "-" + str(lead["attempts"] + 1)
        if db.mark_dialing(lead, request_id):
            used[lead["tenant_id"]] += 1
            busy_phones.append(lead["phone"])
            chosen.append(db.get_lead(lead["campaign_id"], lead["lead_id"]))
    return chosen


def use_call(lead, call):
    if call["state"] == "ended":
        results.handle_result(call["result"])
    else:
        db.mark_active(lead)


def ask_provider(lead):
    code, call = provider.find_call(lead["request_id"])
    if code == 200:
        use_call(lead, call)
    elif code == 404:  # the provider never saw this call
        db.mark_ready(lead)


def dial(lead):
    if not window_ok(lead, provider.sim_now()):  # check again just before sending
        db.mark_ready(lead)
        return
    code, call = provider.place_call(lead)
    if code == 200 or code == 201:
        use_call(lead, call)
    elif code == 504 or code == 0:  # we do not know if it was placed
        ask_provider(lead)
    else:  # 503 etc: not placed, try again later
        db.mark_ready(lead)


def check_stuck():
    for lead in db.stuck_leads(time.time() - 5):
        ask_provider(lead)


def run():
    provider.start_clock()
    db.check_all_again()  # after a restart, check every unfinished call straight away
    while db.count_unfinished() > 0:
        check_stuck()
        for lead in pick_leads():
            dial(lead)
        time.sleep(0.1)
