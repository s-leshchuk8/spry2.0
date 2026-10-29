# Gemini 3.5 replacement — API TEST SUCCEEDED; AWS DEPLOYMENT PENDING

Production remains the previously deployed Nova parser; no AWS resources changed in this phase.
The user reports a successful explicit Gemini 3.5 Flash-Lite request:
`{"status":"validated","model":"gemini-3.5-flash-lite","items":1,"input_tokens":121,"output_tokens":88}`.
This verifies the key/model/structured-output probe, not the future Lambda Secrets Manager path or
end-to-end deployed UI. Defaults now select gemini-3.5-flash-lite, prompt agenda-v2-gemini.
See [Gemini release plan](gemini-release-plan.md) for the current approval-gated setup/deployment.
Earlier 2.5 diagnostic sections below are historical; do not repeat successful tests unnecessarily.

## Secure key entry: next step

From the repository root in your own private VS Code terminal:

```bash
/private/tmp/spry-lab6-venv/bin/python backend/scripts/gemini_key.py
```

This uses the existing local Python environment. If that temporary environment has been removed,
use `cd backend && uv run python scripts/gemini_key.py` instead. Do not pass the key as an argument,
set it in .env/environment variables, paste it in chat, or send a terminal/network screenshot.
The key label `spry-ai-parser` in Google AI Studio is not the key value or an AWS secret name.

The helper uses getpass; input is hidden and stays in process memory, with core dumps disabled.
It refuses pipes/non-TTY input and echoed fallback. The key is neither written to disk nor printed.
Python cannot promise cryptographic zeroing of process memory; this is not a hardware enclave.
Press Enter at the confirmation to discard without any request. **Only after you approve the test**,
type `TEST GEMINI ONCE` at the confirmation after entering the key. That phrase explicitly authorizes
one request using synthetic notes and at most 512 output tokens; there are no automatic retries.
Only validated status/item count/token counts, or sanitized error status, are printed. Test mode
never calls AWS. The assistant has not run this command with a real key.

## API/runtime behavior

- gemini-3.5-flash-lite; generateContent over HTTPS with x-goog-api-key header (never URL query).
- responseMimeType application/json plus responseJsonSchema from the unchanged Pydantic contracts.
  Nullable fields and property ordering preserved; local Pydantic enforces all constraints, including
  schema keywords unsupported by Gemini. Never parse Markdown fences or partially repair unsafe JSON.
- Same external `{agenda, model, prompt_version}` response, model Gemini and prompt agenda-v2-gemini.
- Synthetic/current date and IANA timezone supplied. System instructions delimit pasted text as data;
  no tool execution or database access. JSON/schema failures get at most one fresh corrective attempt
  without echoing unsafe provider output/validation input. Blocked/truncated output fails clearly.
- No HTTP redirects with key headers. Bounded HTTP/Secrets Manager timeouts and response size.
  429 stays busy/429, provider access errors 502, network/server/timeouts 503, invalid output 422.
  Cognito failures retain their existing behavior. Manual agenda/meeting entry remains available.
- Retain usage across validation attempts, including reported thinking tokens, latency and structured
  logs without raw notes/keys/provider messages. PARSER_BILLING_TIER=free is an explicit assumption,
  not a Google billing control; paid estimates use standard $0.30/$2.50 per million tokens.

## Secrets Manager and future deployment — separate approval required

Prepared default secret name: `meetings/gemini-api-key`, region us-east-1/account 891447916595.
After explicit approval to create/update the secret, the owner can re-enter the key with:

```bash
/private/tmp/spry-lab6-venv/bin/python backend/scripts/gemini_key.py --store-secret
```

This is an AWS write. It requires the distinct phrase `STORE SECRET IN 891447916595`; a test
confirmation cannot authorize storage. The helper rejects credential overrides, verifies STS
identity through an explicit spry-friend Session, then uses SDK memory parameters only. It creates
with PROJECT_NAME=meetings and default AWS-managed encryption, or updates an existing correctly
owned/tagged secret. No existing secret is deleted. It prints only the ARN. Do not use a custom
KMS key without a separate permissions review. Existing secret versions remain AWS-managed history.

Future approved parser release:

1. Verify key/model once locally; retain sanitized outcome only. Approve/store the secret and obtain ARN.
2. Build/push one new ARM64 image tag/digest; preserve the currently deployed parser image/config for
   rollback and inspect ECR retention headroom. No backend image update or migration needed.
3. Set non-secret GEMINI_API_KEY_SECRET_ARN and supply reviewed AI_IMAGE_URI; ai-deploy.sh previews by
   default. Template replaces model permissions with GetSecretValue for that exact ARN, keeps logs,
   Cognito/CORS/URL/budget and no VPC/reservation. No CloudFormation secret value is supplied.
4. Review the exact parser change set, including the known dynamic URL dependency marker if present.
   Approve execution separately. Verify deployed URL/auth/config, then approve a bounded real UI parse
   and review/save/reopen. No frontend publication should be needed.
5. Roll back only the parser image/config and matching role policy through a reviewed change set if
   needed. Keep database data, logs and secret history. Do not delete stacks/secrets or downgrade DB.

The existing 5 USD AWS budget is unchanged and does not cap Google API spend. Google Free Tier data
may be used to improve products: use synthetic notes initially and confirm policy before private
meeting content. Instructor approval is required for Gemini instead of the assignment's Claude.

Sources: https://ai.google.dev/api/generate-content and
https://ai.google.dev/gemini-api/docs/structured-output and
https://ai.google.dev/gemini-api/docs/pricing.

## Local validation receipt

Backend suite: **118 passed, 6 skipped** (five PostgreSQL migration cases and one disposable
read-only database case; this provider change requires no migration). Frontend: **43 passed**.
Python lint and changed-file formatting, frontend lint/full formatting, TypeScript/Vite build,
CloudFormation cfn-lint, deployment shell syntax and Git whitespace checks passed. Vite's existing
bundle-size warning remains. No real Gemini/Secrets Manager calls were made: HTTP, secret retrieval,
helper confirmations and storage tests use fakes. Real availability is still unverified.

Changed runtime/tool/config files:
- backend/app/ai/agenda.py, agenda_lambda.py, schema.py; backend/app/config.py.
- backend/scripts/gemini_key.py (new), llm_hello.py; backend/pyproject.toml (remove unused Anthropic dependency).
- infra/ai.yml; infra/scripts/ai-deploy.sh; Makefile.ai; .env.example (ARN only, no key).
Tests: test_agenda.py, test_agenda_lambda.py, test_agenda_api.py, test_deployment_safety.py,
and new test_gemini_key.py under backend/tests.
Documentation: README, ADR 0006, lab6-architecture.md and the current implementation/deployment/
evaluation/runbook notes, plus this Gemini-specific setup/deployment guide.

## First real test: HTTP 404 — diagnosis pending key-scoped model listing

The user ran the hidden-key helper once and reported sanitized status api_error/http_status=404.
No real request was repeated during diagnosis. Helper -> parse_agenda -> GeminiClient.generate uses:

`POST https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash-lite:generateContent`

Model ID, v1beta version and POST method match Google's generateContent reference. The helper forces
that model constant; stale local PARSER_MODEL values cannot change this test's model. Request body
uses contents/systemInstruction/generationConfig, including structured JSON schema. No endpoint,
version, selected model or generation request structure was changed to guess around the 404.

Current primary Gemini Developer API model/deprecation pages state that 2.5 models remain served
but access is limited to prior active users. This makes project/key eligibility a plausible cause,
not a proven diagnosis for this key. Do not infer a global shutdown from a Vertex/Agent Platform
retirement date or a different product's lifecycle table. A displayed quota is not proof of model
availability for a particular key. The raw Google error was intentionally discarded, so its exact
NOT_FOUND reason cannot be recovered from the reported HTTP status alone.

Next safe command, run privately from the repository root:

```bash
/private/tmp/spry-lab6-venv/bin/python backend/scripts/gemini_key.py --list-models
```

Enter the key at the hidden prompt, then type `LIST GEMINI MODELS`. This requests only
`GET https://generativelanguage.googleapis.com/v1beta/models?pageSize=1000`, following bounded
pagination if necessary. It never invokes generateContent, contacts AWS, saves the key, retries
failed requests or selects another model. Only model name and supportedGenerationMethods fields
are emitted; API descriptions, project metadata, page tokens and raw errors are not printed.
It uses the same key header, API version, TLS, timeout/size bounds and redirect protection as the
parser. Listing and generation confirmations are distinct; flags are mutually exclusive.

Look for `models/gemini-2.5-flash-lite` with `generateContent` in its methods. If absent from the
complete listing, it is not advertised to this key on v1beta; use the safe list to review an available
replacement rather than guessing a model name or changing to v1. If present but without the method,
that method is unavailable for this listed model. If present with generateContent, listing alone does
not explain the original 404: confirm key/project consistency and obtain another explicitly approved,
sanitized diagnostic before changing request settings. No automatic generation test follows listing.

References verified during this diagnosis:
- https://ai.google.dev/api/generate-content
- https://ai.google.dev/api/models
- https://ai.google.dev/gemini-api/docs/models/gemini-2.5-flash-lite
- https://ai.google.dev/gemini-api/docs/deprecations


## Additional 404 error-body diagnostics — next request only

The user confirms models.list returned models/gemini-2.5-flash-lite with generateContent. That rules
out an absent catalog entry or missing advertised method; it does not explain the failed generation.
No model change is proposed. The original response body was discarded and cannot be recovered.

The client now reads up to 16 KiB of failed HTTP response body in memory, before closing it. It
retains only a validated numeric Google error_code, allowlisted canonical error_status, and a fixed
redacted error_message summary/category. Raw bodies, error.details, identifiers, arbitrary provider
text, key/header data and agenda text are never printed, logged or written to disk. Unknown/malformed
or oversized error messages are fully redacted. Categories are keyword-based observations, not a
confirmed root-cause decision and never trigger model/configuration changes automatically.
The Lambda response/log contract remains unchanged; only the user-run helper prints these fields.
Body-read/JSON failures retain the original HTTP status. No retries were added.

For one additional test only when explicitly approved, run from repository root:

```bash
/private/tmp/spry-lab6-venv/bin/python backend/scripts/gemini_key.py
```

Enter the key at the hidden prompt, then type TEST GEMINI ONCE only to approve that single
synthetic generation request (512 output-token cap, max_attempts=1). Enter alone cancels. Do not
share the key or unredacted network captures; the helper's sanitized JSON may be shared for diagnosis.
Until that result is available, model eligibility/project access, API-version-specific availability
and request-configuration issues remain possibilities rather than established causes. No real
request, AWS change, deployment, commit or push was performed during this diagnostic update.

## Explicit alternative-model probe (no production/default model change)

After the user reported a 404/NOT_FOUND eligibility diagnostic for 2.5 Flash-Lite, current official
Google Developer API documentation was checked for two stable alternatives:

| Candidate | Structured JSON | Published standard free tier | Project generation access |
|---|---|---|---|
| gemini-3.5-flash-lite | Supported | Text input/output free of charge | User-reported validated request: 121 input / 88 output tokens |
| gemini-3.1-flash-lite | Supported; official guide includes Pydantic JSON-schema extraction example | Text input/output free of charge | Not yet tested |

Recommend **gemini-3.5-flash-lite first**: Google currently recommends it for new projects rather
than restricted 2.5 models. 3.1 Flash-Lite is a valid explicit alternative if appropriate for the
friend's project. These are Gemini Developer API claims, not Gemini chat subscription features.
Free-tier pricing and catalog entries do NOT prove successful generation for this key. The displayed
2.5 limits must not be reused as assumed 3.x quotas; check the candidate's project tier/RPM/TPM/RPD
in AI Studio. No billing upgrade or quota change is performed by the helper.

New --model option is bounded to these two alternatives and the original 2.5 model. It affects only
the injected in-memory client for this single helper probe, not settings/config files, Lambda,
CloudFormation, persistence, prompt contract or default MODEL. It is rejected in --store-secret or
--list-models modes and never triggers fallback to another model. Success output identifies the
actual selected model. No paid-price estimate is reported for these experimental helper probes;
production price assumptions remain unchanged pending model selection.

Only when approving one real test, from repo root:

```bash
/private/tmp/spry-lab6-venv/bin/python backend/scripts/gemini_key.py --model gemini-3.5-flash-lite
```

Enter the key at the hidden prompt; verify printed Test model, then type TEST GEMINI ONCE to
explicitly authorize exactly one synthetic generateContent request (512 output-token cap, no
HTTP/schema retries). Enter instead cancels. The request remains POST on v1beta with the same
structured JSON schema/Pydantic validation, system prompt and redacted error diagnostics. Success
must be an actual validated response; metadata listing or local mocked tests do not establish it.
If it fails, share only the sanitized diagnostic JSON; do not automatically try 3.1 or increase
output limits. A separate explicitly approved 3.1 probe would use --model gemini-3.1-flash-lite.

Only four Python/test files changed for this probe feature, plus this document. No production
model or AWS resources were modified, and no real model/metadata API call, deployment, commit or
push occurred during preparation.

Official sources:
- https://ai.google.dev/gemini-api/docs/models/gemini-3.5-flash-lite
- https://ai.google.dev/gemini-api/docs/models/gemini-3.1-flash-lite
- https://ai.google.dev/gemini-api/docs/pricing
- https://ai.google.dev/gemini-api/docs/deprecations
