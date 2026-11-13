# Submission

## Candidate
- **Name:** Sivasai
- **Assignment chosen:** B (Workflow)
- **Time spent (honest estimate):** about 4 hours (change this to your real time)

## How to run
```bash
# 1. install the libraries
pip install -r requirements.txt

# 2. terminal 1: start the fake phone provider
cd assignment-b-workflow
python -m mock_telephony --speed 1200

# 3. terminal 2: start my program (it writes solution/final_state.csv at the end)
cd solution
python main.py

# 4. run the tests
cd solution
python -m pytest
```
If you want to start again from zero: delete `solution/dispatcher.db` and restart the provider.
If my program stops (even with `kill -9`), just run `python main.py` again. It continues where it stopped.

## Design

**Tools used:** Python, SQLite (a small database file), httpx (to call the provider), Python's built-in
`http.server` (to receive webhooks), pytest (tests).

**Folders:**
```
solution/
  main.py                  start here
  app/
    config.py              settings
    database/              schema.sql (the table) and db.py (all SQL)
    rules/                 scheduling.py (time and order rules)
    services/              provider.py, results.py, dispatcher.py
    api/                   webhook.py (receives results from the provider)
  tests/                   test_scheduling.py, test_results.py
```

**The main idea:** every lead is one row in a database table. The row has a `state` that says what is
happening to that lead. The database file is saved on disk, so if the program stops, nothing is lost.

**Lead states (state diagram):**
```
 ready --we pick it--> dialing --provider accepts--> active --call ends--+--> completed  (customer gave a final answer)
   ^                      |                                              +--> exhausted  (3 calls used)
   |                      +-- provider said "not now" (503) --> ready    |
   +--------------------------------------------------------------------+--> ready (try again later: retry or callback)

 ready --same phone said "do not call" in another campaign--> dnd_blocked
```

**How we avoid calling the same person twice (at-most-once dialling):**
1. Before we call the provider, we first save the lead as `dialing` in the database.
2. Every call has a fixed id (`request_id`) like `c_acme_renewals-ren_0001-1`.
   If we send the same id again, the provider knows it is the same call and does not call twice.
3. If the program stops at any moment, then after restart we ask the provider
   "do you know this id?". If yes, we continue that call. If no, the call never happened, so we try again.

**How the rules are followed:**
- Before dialling we check the time window, the company's call limit, and that the phone is not already in a call.
- Waiting leads are ordered: callbacks first, then retries, then new leads.
- After a call ends, the result decides the next state (see `app/services/results.py`).

## Decisions & assumptions
| Decision | Why | Alternative considered |
|---|---|---|
| Use SQLite and a state column | Simple, saved on disk, easy to explain | Temporal (more setup) |
| Plain functions, no `async` | Easy for a beginner to read | FastAPI and asyncio |
| Put the attempt number inside the `request_id` | Retrying the same attempt reuses the same id | A random id each time (could double-call) |
| Stop making calls a little before the window ends, and check the time again right before sending | The provider can reply slowly and the call may arrive late (this caused 1 mistake in an early test) | Stop exactly at the window end |
| If a call has no result after 5 real seconds, ask the provider about it | Covers lost webhooks, 504 errors and crashes | Only trust webhooks |
| Dial one lead at a time | Simplest code | Many at once (needs threads or async) |

## Failure modes considered
- **503 (provider busy):** the call was not placed, so the lead goes back to `ready` and we try later with the same id.
- **504 or network error (we do not know if the call happened):** we ask the provider using the `request_id`.
- **Same webhook twice:** the second one is ignored, because the lead is no longer waiting for that call.
- **Webhook arrives before the 201 reply:** the result is saved first, and the late 201 changes nothing.
- **Webhook never arrives:** after 5 real seconds we ask the provider ourselves.
- **Wrong signature on a webhook:** we answer 401 and ignore it.
- **Program killed at any moment:** the state is already in the database (see the at-most-once steps above).
- **Not handled:** running two copies of the program at the same time, and there is no `/status` page.

## Testing
- 15 unit tests (`python -m pytest`): window start and end, wrong day, retry waiting times, callback time,
  order of leads, duplicate webhook, 3 attempts means exhausted, and "do not call" blocking the same phone.
- Full runs against the fake provider with `kill -9` during the run.
- Not tested: two copies running together, and clock speeds other than 600x and 1200x.

## Results
In every run the provider reported **0 violations** and my `final_state.csv` matched the provider's `/admin/leads` for all 200 leads.

| Run | Calls made | Violations | Highest calls at once | Leads matching |
|---|---|---|---|---|
| seed 7, speed 1200, killed twice | 407 | 0 | acme 4, zen 3 | 200 of 200 |
| seed 99, speed 600 (default), killed once | 422 | 0 | acme 4, zen 3 | 200 of 200 |
| seed 21, speed 1200, killed once | 417 | 0 | acme 4, zen 3 | 200 of 200 |
| seed 33, speed 1200, killed once | 412 | 0 | acme 4, zen 3 | 200 of 200 |

Callbacks are sometimes called later than needed, because I stop a bit early before a window ends.
This is allowed by the rules, but it makes the "callback lateness" number worse.

## If I had another day
1. Let two copies of the program run together safely.
2. Add a `/status` page that shows progress per campaign.
3. Make callbacks faster by using a smaller safety margin.
4. Test more seeds and more `kill -9`s.
