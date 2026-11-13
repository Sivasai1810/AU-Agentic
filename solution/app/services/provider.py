"""
provider.py - talks to the telephony provider over HTTP (nothing else).

What this file does:
  * start_clock / sim_now : copies the provider's simulated clock and computes "now" locally.
  * place_call            : POST /v1/calls, returns (status_code, json). Code 0 = network error.
  * find_call             : GET /v1/calls?request_id=..., used to check a call we are unsure about.
"""
import time
from datetime import datetime, timedelta

import httpx

from app.config import MY_URL, PROVIDER_URL

client = httpx.Client(timeout=10)
clock = {}


def start_clock():
    while True:  # keep trying until the provider is up
        try:
            data = client.get(PROVIDER_URL + "/v1/clock").json()
            break
        except httpx.HTTPError:
            time.sleep(1)
    clock["epoch"] = datetime.fromisoformat(data["sim_epoch"])
    clock["real"] = data["real_epoch"]
    clock["speed"] = data["speed"]


def sim_now():
    passed_seconds = (time.time() - clock["real"]) * clock["speed"]
    return clock["epoch"] + timedelta(seconds=passed_seconds)


def place_call(lead):
    body = {"request_id": lead["request_id"], "campaign_id": lead["campaign_id"],
            "lead_id": lead["lead_id"], "phone": lead["phone"], "callback_url": MY_URL}
    try:
        r = client.post(PROVIDER_URL + "/v1/calls", json=body)
        return r.status_code, r.json()
    except httpx.HTTPError:
        return 0, None


def find_call(request_id):
    try:
        r = client.get(PROVIDER_URL + "/v1/calls", params={"request_id": request_id})
        return r.status_code, r.json()
    except httpx.HTTPError:
        return 0, None
