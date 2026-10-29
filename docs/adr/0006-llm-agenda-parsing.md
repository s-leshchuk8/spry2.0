# ADR 0006: Suggest agendas outside the trusted write path

Status: deployed and authenticated production parsing verified on 2026-10-29. Instructor approval of the Claude-to-Gemini deviation remains pending.

The assignment required Claude through Bedrock. User-reported Claude access failures led to Nova
Micro; deployed Nova requests are now blocked by verified zero cross-region RPM/TPM and daily token
quotas. The user selected Gemini Flash-Lite in a friend's AI Studio Free Tier project instead.
This further deviation requires instructor approval; no Claude/Bedrock compliance is claimed.

Use one concrete Gemini REST generateContent client, not a provider abstraction or a new service.
Retain ParsedAgenda/AgendaItem/ActionItem and the public response envelope. Use structured JSON,
validate with Pydantic, retry invalid JSON/schema at most once, and never retry rate limits or access
errors automatically. Version the changed system instruction as agenda-v2-gemini. Supply local date
and timezone and treat pasted content as untrusted data. The model cannot write to any database.

Keep the existing outside-VPC parser Lambda, Function URL, JWT authentication, CORS, ARM64 image,
10,000-character limit, logs, manual fallback and explicit review/save. No API/backend/frontend or
migration deployment is needed. Existing Claude/Nova-tagged saved suggestions remain readable.

Retrieve only meetings/gemini-api-key from AWS Secrets Manager via an exact ARN; the environment
contains the ARN, never the key. Use the default AWS-managed Secrets Manager key, avoiding a custom
KMS grant. Cache in process for at most five minutes. Replace Bedrock permissions with only
GetSecretValue for that ARN; retain existing logging policy. Store the actual key via an approved,
user-run hidden prompt helper, never CloudFormation parameters/source/environment files.

The helper refuses non-TTY key input, disables core dumps/logging, does not accept key arguments,
and requires a confirmation phrase after hidden input. Default test mode never contacts AWS and
requests exactly one small synthetic agenda, at most 512 output tokens, no validation/HTTP retries.
Separate --store-secret mode requires separate AWS-write approval and verifies spry-friend account
891447916595/us-east-1 before a named secret write. The user reports the explicit 3.5 test succeeded; secret-storage mode was executed by the owner; only metadata was inspected by the assistant.

Logs retain usage/latency and an explicit free/paid billing assumption. Free-tier reported cost is
zero under that assumption, not a billing guarantee. Published paid-tier estimates are $0.30/$2.50
per million input/output tokens. Secrets Manager incurs separate AWS charges. Free-tier Google
content may be used to improve products; test with synthetic notes and review data policy before
sensitive content. The AWS budget does not cap Google usage.

The exact contract and existing ownership checks remain the trusted persistence boundary.

## Alternatives and consequences

Keeping the parser in the private API VPC would require internet egress (NAT or an appropriate endpoint
for a supported provider); this university lab keeps the existing separate public-egress Lambda and
private database API. Direct Claude API would introduce another credential and did not establish model
access; Bedrock was initially preferred for AWS IAM integration but the tested account could not run it.
A regex-only parser is cheaper/deterministic but handles multilingual unstructured notes and relative
expressions poorly. Gemini is the smallest working substitution and is not literal Claude compliance.
Its availability and Free Tier eligibility can change. Structured output does not establish factual
correctness; manual review and owner-scoped persistence remain mandatory.

Current production evidence: [deployment receipt](../lab6/final-deployment-evidence.json),
[authenticated smoke](../lab6/gemini-authenticated-test.json), [final report](../lab6/final-report.md).
