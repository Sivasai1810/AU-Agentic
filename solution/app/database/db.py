"""
db.py - ALL the SQL lives here (SQLite file dispatcher.db, table defined in schema.sql).

What this file does:
  * Small helpers: run() for writes, query() for reads (each opens its own connection).
  * One function per thing we need: add a lead, list ready/busy/stuck leads,
    move a lead between states (dialing, active, ready) and save a call result.
  * Every update has a "WHERE state = ..." so running it twice does no harm.
"""
import os
import sqlite3
import time

from app.config import ROOT

DB_FILE = os.path.join(ROOT, "dispatcher.db")
BUSY = "state IN ('dialing', 'active')"


def connect():
    conn = sqlite3.connect(DB_FILE, timeout=30)
    conn.row_factory = sqlite3.Row
    return conn


def run(sql, args=()):
    conn = connect()
    with conn:  # saves (commits) when the block ends
        changed = conn.execute(sql, args).rowcount
    conn.close()
    return changed


def query(sql, args=()):
    conn = connect()
    rows = conn.execute(sql, args).fetchall()
    conn.close()
    return rows


def create_table():
    conn = connect()
    with conn:
        conn.executescript(open(os.path.join(os.path.dirname(__file__), "schema.sql")).read())
    conn.close()


def add_lead(campaign_id, lead_id, phone, tenant_id, first_time):
    run("INSERT OR IGNORE INTO leads (campaign_id, lead_id, phone, tenant_id, next_time) VALUES (?,?,?,?,?)",
        (campaign_id, lead_id, phone, tenant_id, first_time))


def get_lead(campaign_id, lead_id):
    return query("SELECT * FROM leads WHERE campaign_id=? AND lead_id=?", (campaign_id, lead_id))[0]


def ready_leads():
    return query("SELECT * FROM leads WHERE state='ready'")


def busy_leads():
    return query("SELECT tenant_id, phone FROM leads WHERE " + BUSY)


def stuck_leads(older_than):
    return query("SELECT * FROM leads WHERE " + BUSY + " AND checked_at < ?", (older_than,))


def count_unfinished():
    return query("SELECT COUNT(*) FROM leads WHERE state IN ('ready', 'dialing', 'active')")[0][0]


def all_leads():
    return query("SELECT * FROM leads ORDER BY campaign_id, lead_id")


def check_all_again():
    run("UPDATE leads SET checked_at=0 WHERE " + BUSY)


def mark_dialing(lead, request_id):
    """Returns False if the lead was changed by someone else (then we must not dial it)."""
    changed = run("UPDATE leads SET state='dialing', request_id=?, attempt_no=attempts+1, checked_at=? "
                  "WHERE campaign_id=? AND lead_id=? AND state='ready'",
                  (request_id, time.time(), lead["campaign_id"], lead["lead_id"]))
    return changed == 1


def mark_active(lead):
    run("UPDATE leads SET state='active', attempts=attempt_no, checked_at=? "
        "WHERE campaign_id=? AND lead_id=? AND " + BUSY,
        (time.time(), lead["campaign_id"], lead["lead_id"]))


def mark_ready(lead):  # the call was never placed
    run("UPDATE leads SET state='ready' WHERE campaign_id=? AND lead_id=? AND state='dialing'",
        (lead["campaign_id"], lead["lead_id"]))


def save_result(lead, new_state, kind, next_time, status, disposition):
    """Save a finished call. The request_id check makes duplicate webhooks do nothing."""
    conn = connect()
    with conn:  # lead update and DND blocking are saved together
        changed = conn.execute(
            "UPDATE leads SET state=?, attempts=attempt_no, kind=?, next_time=?, last_status=?, "
            "last_disposition=? WHERE campaign_id=? AND lead_id=? AND request_id=? AND " + BUSY,
            (new_state, kind, next_time, status, disposition or "",
             lead["campaign_id"], lead["lead_id"], lead["request_id"])).rowcount
        if changed == 1 and disposition == "dnd":
            conn.execute("UPDATE leads SET state='dnd_blocked' WHERE phone=? AND state='ready'", (lead["phone"],))
    conn.close()
