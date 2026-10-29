# Reopen a saved agenda — local fix, deployment pending

## Findings and evidence boundary

The owner reports a successful Ukrainian parse (three topics, one action) and creation of the
synthetic meeting. This is not independently verified database-row evidence. No browser, session
token or private Aurora access is available to the assistant in this run. No new inspector, AWS
write or production query was performed. Whether that specific production agenda row exists is
therefore **not yet confirmed**. Do not re-parse or create another meeting to investigate it.

The existing path is:

1. AgendaDialog review returns `final_agenda` plus unchanged `ai_suggestion` (agenda/model/prompt).
2. MeetingFormDialog explicitly creates the meeting, then POSTs `/api/meetings/{id}/agenda`.
   Failure of the second request leaves the meeting intact and shows a partial-save warning.
3. The backend verifies the current owner, commits one `agendas` row with meeting UUID primary key /
   cascading foreign key; final agenda is JSON, original suggestion is JSONB on PostgreSQL.
   Topics, owners, minutes and actions/deadlines are nested in these JSON columns, not separate tables.
4. GET of the same owner-protected route reads the committed row and returns both JSON documents;
   an owned meeting with no agenda returns JSON null. Other owners receive 404, anonymous requests 401.

Thus a created meeting alone cannot prove the separate agenda POST succeeded. The UI must read back
the agenda. Locally, real disposable PostgreSQL round trips prove every nested field survives saving,
normal meeting editing and reopening, and the original suggestion is preserved.

## Root cause and minimal fix

Edit meeting had no agenda entry point. The calendar popover already opened the editable agenda,
but its `Paste agenda / AI parser` label concealed its saved-agenda purpose.

- Edit meeting now has **View agenda**, above the normal fields. It lazily GETs the existing API and
  displays reviewed title/start/duration/language, all topics with owner/minutes, and all actions with
  owner/deadline. This section is read-only and does not invoke AI, POST, PUT or change a meeting draft.
- Null owners/durations/deadlines have explicit placeholders. Empty/absent agendas, loading and failed
  reads are separate states; Retry only retries the GET. Failed reads are never reported as no agenda.
- Existing calendar action is labelled **View / edit agenda**, reusing the existing editor and API.
- No Gemini, auth, backend source, contract, migration or infrastructure changes are necessary.

Files in this change: front/src/components/SavedAgendaSection.tsx (new),
front/src/components/MeetingFormDialog.tsx, front/src/components/MeetingsCalendar.tsx,
front/src/test/SavedAgendaSection.test.tsx (new), front/src/test/NewMeetingAgenda.test.tsx,
backend/tests/test_agenda_api.py, and this documentation/current verification records.

## Tests

Frontend: **47 passed**; ESLint, Prettier and TypeScript/Vite build pass. Regressions cover
on-demand full display, no parser/writes, preservation of unsaved meeting edits, absence/error/retry,
empty collections, and parse → review → create → reopen with three topics and a dated action.
The UI round trip uses mocked HTTP; backend PostgreSQL tests supply actual persistence evidence.
Backend SQLite: **150 passed, 6 PostgreSQL-only skipped**. Backend disposable PostgreSQL:
**156 passed, zero skipped**. Owner round-trip tests cover all nested fields after ordinary meeting
updates for historical Claude/Nova and current Gemini metadata. Only test code changed on the backend.
Owned disposable container/volumes removed. Ruff check/format and Git whitespace pass.
Vite's existing >500kB bundle warning remains non-blocking. No real inference was requested.

## Check the production row now, without deployment

Click the existing synthetic event in the calendar, then its **Paste agenda / AI parser** action
(in the popover, not Edit meeting). The current deployed editor already GETs the saved agenda.
If it shows the three reviewed topics and action/deadline, this confirms owner-authenticated readback.
Do not click Parse or Save just to inspect it. Alternatively inspect only that GET's Response in
DevTools: `final_agenda` and `ai_suggestion` versus HTTP 200/null or an error. Share only synthetic
response JSON; never headers, cookies, tokens, HAR or Copy as cURL. Preserve its original suggestion.

## Frontend-only deployment — requires explicit approval; NOT executed

Run from the repository root in bash. Do not use aggregate `make aws-deploy`/`aws-frontend-deploy` or
`aws-frontend-publish`: those can change other services or use S3 --delete. Reuse the existing URL,
Cognito public settings, bucket and distribution. No stack/image/parser/backend/migration deployment.
All AWS calls below use the account-guard wrapper with explicit profile/region.

```bash
set -euo pipefail
export AWS_PROFILE=spry-friend AWS_REGION=us-east-1
source infra/scripts/aws-target.sh
aws_target_init # abort unless Account == 891447916595; refuses credential overrides
RELEASE_TAG="lab6-agenda-view-$(date -u +%Y%m%dT%H%M%SZ)"
BACKUP_DIR="/private/tmp/spry-$RELEASE_TAG-backup"
bash infra/scripts/frontend-backup.sh "$BACKUP_DIR"
# The helper refuses an existing path and verifies index.html/checksums. Keep all older backups.

output() {
  aws_spry cloudformation describe-stacks --stack-name "$1" \
    --query "Stacks[0].Outputs[?OutputKey=='$2'].OutputValue | [0]" --output text
}
export VITE_API_URL="$(aws_spry lambda get-function-url-config \
  --function-name meetings-backend --query FunctionUrl --output text)"
export VITE_AGENDA_PARSER_URL="$(aws_spry lambda get-function-url-config \
  --function-name meetings-agenda-parser --query FunctionUrl --output text)"
export VITE_COGNITO_REGION=us-east-1
export VITE_COGNITO_USER_POOL_ID="$(output meetings-cognito UserPoolId)"
export VITE_COGNITO_CLIENT_ID="$(output meetings-cognito UserPoolClientId)"
export VITE_COGNITO_DOMAIN="$(output meetings-cognito HostedUiDomain)"
export VITE_COGNITO_GOOGLE="$(output meetings-cognito GoogleEnabled)"
for name in VITE_API_URL VITE_AGENDA_PARSER_URL VITE_COGNITO_USER_POOL_ID \
  VITE_COGNITO_CLIENT_ID VITE_COGNITO_DOMAIN VITE_COGNITO_GOOGLE; do
  value="${!name}"
  test -n "$value" && test "$value" != None && test "$value" != null
done
BUCKET="$(output meetings-frontend BucketName)"
DISTRIBUTION="$(output meetings-frontend DistributionId)"
test "$BUCKET" = meetings-frontend-sitebucket-la6ugmfuat3e
test "$DISTRIBUTION" = E32YSLDLU597TU
test "$VITE_API_URL" = https://d4i7z5o3jzr2rwpjfdecpzph4y0kzvnp.lambda-url.us-east-1.on.aws/
test "$VITE_AGENDA_PARSER_URL" = https://3vbrnjgxdcbbrxlfmih6f3sxcy0nvbwb.lambda-url.us-east-1.on.aws/
(cd front && npm test && npm run lint && npm run format:check && npm run build)
# Inspect build: both existing URLs, Cognito public settings and View agenda must be present.
# Approved writes begin here. Assets first, HTML last; preserve all unrelated/old objects.
aws_spry s3 sync front/dist "s3://$BUCKET" --exclude index.html \
  --cache-control 'public,max-age=31536000,immutable' --only-show-errors
aws_spry s3 cp front/dist/index.html "s3://$BUCKET/index.html" \
  --cache-control no-cache --content-type text/html --only-show-errors
INVALIDATION="$(aws_spry cloudfront create-invalidation --distribution-id "$DISTRIBUTION" \
  --paths '/*' --query Invalidation.Id --output text)"
aws_spry cloudfront wait invalidation-completed --distribution-id "$DISTRIBUTION" --id "$INVALIDATION"
```

The BucketName/DistributionId keys match infra/frontend.yaml; verify their live values as above.
Stop on changed endpoints, missing Cognito values, unexpected targets or failed backup/checks.
Retrieve served index/assets to verify hashes against this build after invalidation. No --delete.

### Live verification after approved publication

Hard refresh → open the existing synthetic meeting → Edit meeting → View agenda. Capture all three
saved topics and the action, checking owner/duration/deadline against the original synthetic response.
Close/reopen once; ordinary meeting fields must be unchanged. No parsing or new meeting is needed.
If response is null, report the missing agenda; do not invent a row or silently regenerate it.
If an error, stop and inspect the read request; no parser permission changes are justified by it.

### Rollback

If the frontend fails, propose restoring the new verified backup's assets and index (index last),
without --delete, then invalidate the same distribution. Obtain approval before rollback publication.
No records, backend/parser versions, stack resources or existing assets need to be deleted.
