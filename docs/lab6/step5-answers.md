# Step 5 written answers

## Which inputs went wrong and what fixes them?

Real-run answer is pending the five deployed evaluations; no accuracy outcome is claimed.
Classify failures after collecting outputs: missing facts/names → prompt examples or extraction
instruction; wrong types/ranges → schema/validation; relative-date ambiguity → preserve null and
ask the reviewer; an unsupported yet well-formed fact → review/UI or additional grounded checks,
not merely stricter JSON syntax. Record the failing input and actual JSON before choosing a fix.

## What did injection input 5 do?

Observed behavior of this injection case remains pending the five-case UI evaluation. The system prompt says source text is data, names must be
copied, and missing facts stay empty. This does not prove the model will resist injection. Even
if it replaces owners, those owners remain plain text in an editable suggestion; no write tool
exists, the parser has no DB access, and only the human's authenticated, owner-scoped Save writes.
The UI does not interpret model strings as HTML or execute model-supplied links.

## Cost: 20 organisations, 30 agendas per week

Use the mean of real `cost_usd` values (including retries/failures with known usage), called `c`.
Monthly parses are `20 × 30 × 52 / 12 = 2,600`; inference estimate is `2,600 × c` USD/month.
If using a four-week month, report that assumption and use 2,400 instead. Compare with $7.30:
endpoint break-even at `c = 7.30/2600 ≈ $0.002808` per parse. The endpoint would be an additional
fixed cost, not a substitute for inference charges.

Current deployment declares Gemini Free Tier, so returned `cost_usd=0` is an assumption, not an invoice
or guarantee of eligibility. The existing authenticated smoke used 124 input / 88 output tokens and
1,831 ms. The five-case mean is pending and must not be replaced with that one smoke result.
For a paid-tier scenario, apply the pricing recorded in the release documentation ($0.30 input /
$2.50 output per million tokens) to observed usage and recheck Google pricing before billing changes.
AWS Secrets Manager, Lambda, logs, image storage and existing infrastructure are additional costs;
the $5 AWS budget sends alerts and neither caps spend nor monitors Google charges. An extra $7.30/month
endpoint is unnecessary for the current outside-VPC Gemini parser and would not replace model charges.
Claude was the original requirement; Gemini substitution needs instructor approval.

## How to compare agenda-v2 with agenda-v1 using 500 corrections?

Freeze a de-identified, permission-scoped evaluation set of original inputs, local date/timezone,
original suggestions/model/prompt metadata, and reviewed final agendas. Suggestions alone are
insufficient to replay a prompt: the current application intentionally does not store raw pasted
text, so collect consented source inputs separately for evaluation. Audit a sample of final agendas
as human edits are not automatically ground truth. Split development and held-out cases; do not
tune on the held-out set. Run both prompts on the same held-out inputs/model and measure per-field
accuracy, invented-fact rate, omitted-fact rate, parse failure rate, correction rate, latency and
cost. Match topics/actions by content rather than list position; preserve exact owner spelling and
normalize equivalent dates. Report aggregate scores and categories/languages, paired differences
and uncertainty (e.g. bootstrap intervals). Promote v2 only if improvements hold without increasing
invented facts or regressing important categories; keep both prompt versions reproducible.
