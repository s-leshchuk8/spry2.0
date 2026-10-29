# Gemini parser deployment result

Account/profile/region verified: spry-friend / 891447916595 / us-east-1.
Only the approved parser release was deployed. Stack meetings-ai is UPDATE_COMPLETE.

- Release `lab6-gemini35-20261029t204550z-53486889`, immutable ARM64 image `891447916595.dkr.ecr.us-east-1.amazonaws.com/meetings-backend@sha256:9d97bc4d661c2acb60f5838d9dcd3a2c73598c3a1ba1ff2a98b28b3544744397`.
- Owner used hidden-input helper to create/update only meetings/gemini-api-key; assistant inspected
  metadata only, never read its value. ARN `arn:aws:secretsmanager:us-east-1:891447916595:secret:meetings/gemini-api-key-SZI39j`.
- Change set `arn:aws:cloudformation:us-east-1:891447916595:changeSet/preview-lab6-gemini35-20261029t204550z-53486889/ddb5d92e-ee70-4f65-80a4-7290984c2794` reviewed and executed: parser function and IAM role updated
  in place. The expected dynamic URL dependency marker did not change the actual URL.
- Model gemini-3.5-flash-lite, prompt agenda-v2-gemini, PARSER_MOCK=0, billing assumption free.
- Role has GetSecretValue for only the exact ARN plus existing standard logging policy. No Bedrock
  invocation policy remains. The environment has ARN only, no plaintext key or DB credentials.
- Outside VPC, existing log group/Cognito/CORS/URL preserved, no reserved concurrency. Anonymous
  POST returns 401 and browser-origin CORS preflight passed without model invocation.
- Backend image/revision/hash metadata and frontend index ETag/length/modified baseline unchanged.
  No database, migration, Cognito, frontend, CloudFront or unrelated stack changes.
- Existing ECR images preserved; no repository/retention policy change or resource deletion.
- Rollback metadata is private at `/private/tmp/spry-gemini35-release-53486889`. No rollback was performed and none is proposed now.

The intended secret and one ECR image are the new AWS artifacts; parser Lambda/role configuration
are updated. Secrets Manager charges approximately $0.40/secret-month + $0.05/10,000 API calls before
credits, with ordinary existing Lambda/log/image-storage usage. Google Free Tier assumption is not
an automatic spending cap. Existing meetings-monthly-5usd budget is unchanged.

## Real authenticated verification — PASSED

The signed-in user confirmed editable suggestions appeared after exactly one requested UI parse of
synthetic notes. Read-only CloudWatch inspection found exactly one matching agenda_parsed event:
Gemini 3.5 Flash-Lite, prompt agenda-v2-gemini, outcome success, 124 input tokens, 88 output tokens,
1,831 ms parser latency. Logged cost_usd=0 under the explicit free-tier assumption (not an invoice).
No further inference request was issued by the assistant. This verifies the authenticated deployed
UI -> Cognito-protected Lambda -> Secrets Manager -> Gemini -> validated review path. No meeting
creation/save was requested, so persistence and owner-isolation E2E checks remain separate.
Sanitized receipt: gemini-authenticated-test.json; no user IDs, tokens, keys or source text included.

Remaining submission work: finish five real evaluation cases, confirm explicit review/save/reopen and owner
isolation using existing users, capture a real sanitized log line and <=45-second video, document
instructor-approved Gemini deviation from Claude, then separately approve final Git commit/push.
No commit or push occurred. Approval for the single synthetic parse is already granted; no need
to ask for it again, only the user's signed-in session/action is missing.
