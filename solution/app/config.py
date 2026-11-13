"""
config.py - settings shared by all files.

What this file does:
  * Finds the fixtures folder and reads campaigns.json once.
  * Gives easy names: cfg (whole file), campaigns (by id), tenant_limit (max calls per tenant).
  * Holds the provider address and our own webhook address.
"""
import json
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # the solution/ folder
FIXTURES = os.path.join(ROOT, "..", "assignment-b-workflow", "fixtures")
PROVIDER_URL = "http://127.0.0.1:8099"
MY_URL = "http://127.0.0.1:8200/webhooks/telephony"

cfg = json.load(open(os.path.join(FIXTURES, "campaigns.json")))
campaigns = {}
for c in cfg["campaigns"]:
    campaigns[c["campaign_id"]] = c
tenant_limit = {}
for t in cfg["tenants"]:
    tenant_limit[t["tenant_id"]] = t["max_concurrent_calls"]
