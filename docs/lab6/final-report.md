# Lab 6 final verification report

Updated 2026-10-29. Production deployment and one authenticated parse are verified; five-case
accuracy evaluation, live save/reopen and submission media remain pending manual assistance.
No browser is connected and no browser verification is claimed. Do not reconnect automatically.

## Architecture and deployment evidence

React/TypeScript on S3/CloudFront uses Cognito ID tokens. A separate ARM64 Lambda outside the private
VPC calls Google Gemini 3.5 Flash-Lite using structured JSON, validates the unchanged Pydantic agenda
contract, and returns editable suggestions. The owner explicitly saves via the normal owner-scoped
FastAPI API into private Aurora. The model has no write tools or DB credentials.

Account 891447916595 / spry-friend / us-east-1. Production https://d17yxyt8by6ov0.cloudfront.net/.
[Current read-only AWS receipt](final-deployment-evidence.json) verifies stack UPDATE_COMPLETE,
Lambda Active/Successful, ARM64, 30s/512MB, no VPC subnets, mock off, exact model/prompt, existing
URL/CORS and $5 budget with 80%/100% email notifications. Secrets Manager key value was not read.
See [deployed release receipt](gemini-deployment-result.md) for image digest and secret ARN.
[Sanitized authenticated smoke](gemini-authenticated-test.json): 124 input / 88 output tokens,
1,831ms, success, declared Free Tier cost $0. No meeting was saved by that smoke.

## Model substitution and limits

Original assignment required Claude through Bedrock/Mantle and record_agenda tool extraction.
The owner reported AccessDenied for Claude Opus 5.5 and Haiku 5.5; these denials were not reproduced
in this final pass. Nova Micro was deployed but account-applied cross-region RPM/TPM/daily quotas
were zero despite an active authorized inference profile: [recorded evidence](nova-quota-evidence.json).
Gemini 2.5 appeared in ListModels but generation returned an eligibility-related 404; model listing
was not treated as proof of access. The owner's Gemini 3.5 probe and authenticated deployed parse
succeeded. Production uses Gemini REST generateContent structured JSON, not Anthropic Messages,
Bedrock Converse, or the original record_agenda tool. **Instructor approval is required; literal
Claude-specific compliance is not claimed.** Contract, validation, review and persistence are preserved.

Version agenda-v2-gemini supplies local date/timezone and treats pasted text as untrusted data.
One corrective schema retry is allowed; transport/rate failures are not automatically retried.
Structured JSON validation cannot prove factual accuracy. Relative dates may remain ambiguous;
users must review suggestions. Cancellation stops UI waiting but cannot guarantee cancellation of
an upstream request. Raw source notes are not retained for training/evaluation replay.

## Security and cost

Cognito JWT validation, 10,000-character input limit, CORS and owner-scoped save remain enabled.
The Lambda has an exact secret ARN and GetSecretValue permission, not a plaintext Gemini key;
key entry used the hidden-input helper. Memory cache avoids unnecessary secret reads. No Bedrock
permission or database access is needed by the parser. Structured application logs contain metrics
and a subject identifier; submission exports remove that identifier and never include raw notes,
credentials, headers or cookies. Synthetic inputs only for Free Tier tests; review Google's data
policy before using sensitive material. API/model availability and project limits can change.

Logged zero cost under `free` is a declared estimate, not an invoice. Secrets Manager is approximately
$0.40/secret-month + $0.05/10,000 calls before credits; existing Lambda/logs/ECR/Aurora/hosting charges
remain separate. The AWS $5 budget alerts, rather than prevents, spending and excludes Google billing.
Recheck published pricing before changing billing tier. See [Step 5 cost calculation](step5-answers.md).

## Actual local validation

- Backend SQLite: 150 passed, 6 intentionally PostgreSQL-only skips.
- Backend disposable PostgreSQL 16: **156 passed, zero skips** (including read-only inspection,
  migration compatibility, owner isolation and final/original agenda persistence).
- Full-chain disposable rehearsal: 0003 without agendas → 0004_reviewed_agendas, data fingerprints
  unchanged, schema/FK/index/cascade checks passed; repeating upgrade preserves state; five focused
  tests passed. Owned temporary containers/volumes were removed.
- Frontend: **43 passed**, ESLint, Prettier and TypeScript/Vite build passed.
- Ruff check/format on all backend files passed; all infra YAML/YML passed cfn-lint;
  shell syntax checks and Git whitespace check passed.
- Build warning: bundled JavaScript exceeds 500kB; non-blocking for the lab, no unrelated redesign.

Final style cleanup formatted the already corrected historical migration and synchronized its
unapplied-only repair patch; revision/dependencies and SQL behavior are unchanged. No production
migration was rerun. The manual CI publication example no longer uses S3 `--delete`, preserving
unrelated objects. No CI workflow was executed. Existing report-module changes are earlier style
cleanup; no report functionality was redesigned. User-owned .vscode settings are not generated caches.

## Acceptance status

| Criterion | Evidence / status |
|---|---|
| Exact agenda contracts; null unknowns; versioned prompt; local date/tz | Source + automated tests pass; factual extraction measured separately |
| Claude / Bedrock / record_agenda requirement | Deviation; instructor approval outstanding |
| Separate parser, shared image pattern, 30s/512MB, no NAT | Deployed architecture and receipt verified |
| JWT, max input, CORS, URL, logs, $5 budget | Source/tests + read-only deployment/budget receipt |
| Paste → progress/cancel → editable badges → explicit confirmation; manual fallback | Frontend tests pass; real review screen confirmed by owner; full live flow pending |
| Original suggestion/model/prompt retained; owner-scoped persistence | Automated PostgreSQL/API tests pass; live save/reopen pending |
| Cross-user isolation | Automated authenticated read/write 404 and anonymous 401 pass; live two-account unverified |
| Five required inputs, actual raw JSON, invented values, tokens/cost/latency | Inputs/expectations prepared; real results pending; do not substitute mocked outputs |
| Sanitized real CloudWatch line | Authenticated smoke receipt available; per-case attribution pending |
| Step 5 written answers | Cost/comparison method prepared; empirical failure/injection answers pending |
| ADR and C4 parse/save diagram | Updated; explicit alternatives, security, provider deviation |
| Deployed <=45s GIF/MP4 showing one edit and save | Script prepared; recording pending |
| Commit link | Not authorized yet; no commit/push performed |

## Remaining work

Follow [manual verification](manual-verification.md) for five single-click cases and one approved
synthetic save/reopen. Report time/timezone, screenshots and synthetic response JSON; assistant then
correlates read-only CloudWatch logs and completes empirical results. A second authorized account is
optional for additional live isolation evidence; it is not available to the assistant. Preserve the
synthetic record and all unrelated production data. Record the video, obtain instructor acceptance
of the substitution, review final staged files, then separately authorize commit/push. No additional
infrastructure resources or application deployments are required for this verification plan.

## Saved-agenda usability correction (local, awaiting frontend publication)

The owner reports case 1 returned three topics and one action and that the synthetic meeting was
created. Raw response, matching metrics and authenticated saved-row readback remain pending.
Edit meeting lacked an agenda entry point even though its calendar popover could open the existing
agenda editor. A read-only View agenda section now uses the existing owner-protected GET and shows
all saved topics/actions/owners/durations/deadlines. The calendar action is renamed View / edit agenda.
Frontend tests now **47 passed**; backend remains **156 passed** on disposable PostgreSQL. Style/build
checks pass. No backend implementation, parser, auth, migration or infrastructure changes were made
for this fix, and it is not deployed. See [exact plan and evidence limits](saved-agenda-fix.md).
