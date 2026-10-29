# Lab 6 deployment result

Completed UTC: 2026-10-29T18:52:00.542603+00:00.
Account `891447916595`, profile `spry-friend`, region `us-east-1`, project `meetings`.
Release `lab6-nova-20261029t182318z-cf9bc2e1`.
Live app: https://d17yxyt8by6ov0.cloudfront.net.

## Verified prerequisites

Reused the completed Aurora snapshot `meetings-pre-lab6-nova-20261029t182318z-cf9bc2e1`, verified available, and the intact
existing frontend backup `/private/tmp/spry-release-lab6-nova-20261029t182318z-cf9bc2e1/frontend-backup`. No snapshot or backup was recreated.
Registry release tag/digest and reviewed ARM64 config digest matched; both change sets matched
saved Changes/Parameters/Capabilities/IDs and were available before execution. Lambda baselines
matched the saved preview state. No new images or change sets were built/created.

## Backend

Executed only `arn:aws:cloudformation:us-east-1:891447916595:changeSet/preview-lab6-nova-20261029t182318z-cf9bc2e1-api/8675094c-e776-4d66-865a-53a434cf3cd6`.
Stack UPDATE_COMPLETE; Active/Successful Lambda; ARM64; reviewed immutable image digest
`sha256:5641619e538ae30a6f1ca21909998236841ef05ca54623e654da2c25272d0782`;
Seed=false and Cognito configuration present. Backend Function URL unchanged. DB-backed health
returned HTTP 200 with status ok before and after migration.

## Production migration and preservation

A unique private VPC verifier first confirmed live revision 0003, agendas absent, and exact original
meeting/constraint/column metadata. Fixed SELECTs captured private counts and complete-row aggregate
fingerprints for users, meetings, participants and meeting_participants. No row values were returned.
Verifier used TLS, default read-only transactions, 20-second connection timeout, 5-second statement
and 1-second lock timeouts; rollback and close always. No endpoint, IAM policy or network change.

The existing backend migrate action was invoked exactly once with Seed=false, running only the
rehearsed chain `0003 -> 5d5e3ded4830 -> 0004_reviewed_agendas`. Handler returned status migrated.
Independent read-only postcheck confirmed:

- Recorded revision exactly 0004_reviewed_agendas.
- agendas: meeting_id UUID NOT NULL primary key; final_agenda JSON NOT NULL;
  ai_suggestion JSONB nullable.
- Validated cascade FK to meetings(id), validated primary key, exactly one unique supporting index.
- Existing table column/constraint/index metadata unchanged.
- Existing application-table counts and complete-row fingerprints identical before/after.

Sanitized deployed metadata: `deployed-schema.json`. Original pre-release snapshot remains
`database-inspection-result.json`; it was not overwritten. Private preservation evidence remains
outside Git in `/private/tmp/spry-release-lab6-nova-20261029t182318z-cf9bc2e1/private-inspector-ecb41fb3`.

Temporary verifier ARN: `arn:aws:lambda:us-east-1:891447916595:function:meetings-release-verify-ecb41fb3afc4`. After ownership/code-hash checks, only that newly
created function and its own tagged log group were deleted and verified absent. No pre-existing
resource was deleted. No downgrade/stamp/reset or meeting/user data update was executed.

## Parser

Executed only `arn:aws:cloudformation:us-east-1:891447916595:changeSet/preview-lab6-nova-20261029t182318z-cf9bc2e1-parser/7a0b1d9a-d9f1-44fd-935d-9fa640547349`.
Stack UPDATE_COMPLETE; Active/Successful Lambda; same reviewed ARM64 digest; Nova Micro
`us.amazon.nova-micro-v1:0`, prompt agenda-v1, PARSER_MOCK=0, no DB environment variables,
no VPC, no concurrency reservation, existing parser CloudWatch group. Verified actual model-scoped
InvokeModel policy, Cognito and URL CORS. Unauthenticated and invalid-token POSTs return 401.
The conditional URL marker did not result in a URL change: parser URL is identical to baseline.

A local verifier initially expected an unused CORS_ORIGINS environment variable. Its check was
corrected to inspect actual Function URL CORS and verification passed without a deployment retry.

## Frontend

Revalidated the existing backup before publishing. Built with live backend/parser URLs and
matching Cognito client/pool/region/domain settings. Verified compiled JS contains public endpoint
and auth configuration. Published assets first, index last, with NO --delete and no unrelated
object writes. All prior S3 object keys remain; unrelated object ETags unchanged.
Bucket `meetings-frontend-sitebucket-la6ugmfuat3e`, distribution `E32YSLDLU597TU`.
Invalidation `I4S7P1S1MR58O57F6UF75X36G4` completed. Live index and referenced CSS/JS match local build
SHA256 checksums and return HTTP 200. Build passed with the existing bundle-size warning.

## Bounded smoke results

Backend health 200; unauthenticated /api/me and /api/meetings 401; parser missing/invalid tokens 401;
parser CORS preflight passed; frontend 200 with exact served build verified. CloudWatch error scans
from each updated Lambda's LastModified found 0 error/traceback/timeout/runtime-exit events in both
groups. This is a bounded observed window, not a guarantee against future errors or log ingestion lag.
No authenticated CRUD or full signed-in browser workflow was performed; no real model invoked.

## Remaining laboratory tasks

1. Sign in with an existing account and approve bounded real Nova inference. Verify Ukrainian
   paste -> parse -> edit -> explicit save -> reopen, original-suggestion metadata and manual entry.
2. Execute five real evaluation cases; verify cross-user ownership isolation using existing accounts.
   Collect actual output, usage, latency/cost and a real agenda_parsed CloudWatch line.
3. Record <=45-second walkthrough; complete evaluation/submission documents. Instructor approval for
   Nova instead of original Claude requirement remains necessary; do not claim Claude compliance.
4. Review and separately authorize final Git commit/push. Neither was performed.

Known follow-up: ECR retention is live at 10 and local template matches, but the stored
meetings-backend-ecr stack template still says 5. Reconcile through a separately reviewed update
before reusing that stack's deployment path. It does not block the deployed app.

No rollback was needed. Existing Aurora snapshot/frontend backup/prior image references remain
available. If needed, restore a reviewed prior application image/frontend while preserving new
agenda data; never drop/downgrade/stamp/reset the database. No paid Bedrock calls occurred.
