# AI Usage Disclosure

## Tools used
- Claude


## What I used them for
- Helped organize the implementation and understand the responsibilities of different modules.
- Generated and refined context comments at the top of each source file to explain its purpose and responsibilities.
- Improved code comments to make the implementation easier to read and maintain.
- Assisted with implementing and refining the rule-processing loop, including scheduling, eligibility checks, retries, callbacks, and lead state transitions.
- Helped identify edge cases and think through failure scenarios such as duplicate webhooks, provider timeouts, and application restarts.
- Used AI to explain unfamiliar concepts and review implementation approaches.

## What I wrote or decided myself
- The overall approach and architecture of the campaign dispatcher.
- The lead lifecycle and the rules governing fresh calls, retries, callbacks, and terminal states.
- How campaign calling windows, tenant concurrency limits, and global phone restrictions should be enforced.
- The decisions about when a lead should remain active or move to the completed state.
- Reviewing the generated implementation, understanding the logic, and deciding which suggestions to adopt.

## Where the AI was wrong or unhelpful
- Some initial suggestions introduced unnecessary complexity, especially around database structure and lead lifecycle tracking.
- Some proposed approaches did not fully account for the campaign calling-window boundaries and simulated clock behavior.
- I questioned these suggestions, compared them against the assignment requirements, and refined the implementation accordingly.

## How I verified AI-generated code
- Read through the implementation and comments to understand the responsibilities of each module.
- Ran the unit tests using pytest.
- Tested scheduling rules, retry timing, callback handling, and lead state transitions.
- Ran the application against the mock telephony provider.
- Tested application restarts using `kill -9` and checked whether processing recovered correctly.
- Compared the generated `final_state.csv` against the provider's `/admin/leads` results and checked `/admin/report` for violations.