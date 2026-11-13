"""
main.py - start here:  python main.py   (mock provider must already be running)

What this file does:
  1. Creates the SQLite table and loads the leads from the CSV files (safe to repeat).
  2. Starts the webhook server and the dispatcher loop.
  3. When every lead is finished, writes final_state.csv (sorted by campaign_id, lead_id).
Stop it any time (even kill -9) and run it again: it carries on from the database.
"""
import csv
import os

from app.api import webhook
from app.database import db
from app.services import dispatcher
from app.config import FIXTURES, ROOT, campaigns, cfg


def load_leads():
    for campaign in campaigns.values():
        for row in csv.DictReader(open(os.path.join(FIXTURES, campaign["leads_file"]))):
            db.add_lead(campaign["campaign_id"], row["lead_id"], row["phone"],
                        campaign["tenant_id"], cfg["sim_start"])


def write_final_csv():
    with open(os.path.join(ROOT, "final_state.csv"), "w", newline="") as f:
        out = csv.writer(f)
        out.writerow(["campaign_id", "lead_id", "final_state", "attempts", "last_status", "last_disposition"])
        for lead in db.all_leads():
            out.writerow([lead["campaign_id"], lead["lead_id"], lead["state"], lead["attempts"],
                          lead["last_status"], lead["last_disposition"]])


if __name__ == "__main__":
    db.create_table()
    load_leads()
    webhook.start()
    dispatcher.run()
    write_final_csv()
    print("all leads finished, final_state.csv written")
