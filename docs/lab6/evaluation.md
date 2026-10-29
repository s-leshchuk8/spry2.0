# Lab 6 five-case evaluation

Production uses **gemini-3.5-flash-lite**, prompt **agenda-v2-gemini**, mock off.
The authenticated smoke test passed; it is separate from these five assignment cases.
See [smoke evidence](gemini-authenticated-test.json) and [deployment receipt](final-deployment-evidence.json).
These five real outputs are **pending user-assisted UI execution**. No measurements are fabricated.

| # | Case | Actual JSON / error | Correct / incorrect fields | Invented values | Tokens in/out | Cost USD | Latency ms |
|---|---|---|---|---|---|---|---|
| 1 | Ukrainian / multiple topics | pending | pending | pending | pending | pending | pending |
| 2 | English email | pending | pending | pending | pending | pending | pending |
| 3 | Relative / ambiguous dates | pending | pending | pending | pending | pending | pending |
| 4 | Non-agenda | pending | pending | pending | pending | pending | pending |
| 5 | Prompt injection | pending | pending | pending | pending | pending | pending |

Exact inputs and expected findings are in [evaluation-cases.json](evaluation-cases.json).
Instructions and capture checklist: [manual-verification.md](manual-verification.md).

For each case capture the unedited parser Response body, HTTP status, local date/timezone and click time.
Only copy synthetic request text / response JSON, never Authorization headers, cookies, or a HAR export.
Validation checks Pydantic shape separately from factual accuracy. Count unsupported but schema-valid
values as invented. Treat a refusal or 422 as an observed outcome, not as a successful extraction.
For non-agenda input, an empty valid agenda or explicit refusal is semantically acceptable; creating
shopping topics is a failure. Relative expressions require a documented interpretation; uncertainty
is a review requirement, not evidence for an invented exact hour.

After the user reports the case times/results, correlate read-only CloudWatch agenda_parsed events
in chronological order. Keep only event/model/prompt_version/input_tokens/output_tokens/latency_ms/
cost_usd/billing_tier/outcome and timestamp. Exclude user IDs and unrelated requests. If concurrent
traffic prevents reliable matching, mark attribution uncertain rather than inventing a match.
Five button clicks may cause up to ten provider calls because schema validation retries once;
there are no automatic HTTP/rate-limit retries. Space clicks at least 30 seconds apart and stop
on a rate-limit error. The former 2.5 model's displayed quotas are not proof of 3.5 quotas.

Claude was specified by the assignment. These are Gemini results and require instructor approval.
