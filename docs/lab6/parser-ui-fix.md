# AI parser discovery fix — deployed

Production: https://d17yxyt8by6ov0.cloudfront.net. Verified account spry-friend / 891447916595 / us-east-1.

## Root cause

The previous deployed bundle already contained AgendaDialog and the correct parser endpoint.
It was only reachable from an existing calendar meeting's details under Add / view agenda.
The New meeting dialog contained only manual fields, with no parser entry point. This was a
frontend workflow/discoverability gap, not missing Lambda deployment or parser configuration.

## Change

- New meeting now shows **Paste agenda / AI parser** above Title.
- It opens the reused AgendaDialog in draft mode: paste -> Parse with AI -> review/edit ->
  Use reviewed agenda. No meeting/agenda is written during parsing or draft review.
- Return to the meeting fields, confirm date/time/location and explicitly Create meeting to save
  the meeting and reviewed agenda through the existing APIs. Reviewed agenda title prefills the
  meeting title; agenda schedule metadata remains separate, so confirm the meeting time manually.
- Original AI suggestion/model/prompt metadata is preserved independently of edits.
- If agenda persistence fails after meeting creation, the UI explains the partial save and reuses
  that meeting on retry instead of creating a duplicate. Closing retains the created meeting;
  its agenda can be edited later from its details.
- Existing meeting details now use the same clear Paste agenda / AI parser button label.
- Manual creation and parser failure/manual agenda fallback remain available.

Files: front/src/components/AgendaDialog.tsx, MeetingFormDialog.tsx, MeetingsCalendar.tsx;
front/src/test/AgendaDialog.test.tsx, NewMeetingAgenda.test.tsx; this report.
No backend, API contract, parser Lambda, database, migration, IAM, Cognito or ECR changes.

## Validation and publication

Frontend suite: **42 passed**. ESLint, complete Prettier check, TypeScript/Vite build and Git
whitespace check passed. Existing bundle-size warning remains. New tests cover draft review,
no persistence before explicit creation, original suggestion preservation, reopening edited draft,
partial-save retry without duplicate meetings and cancel/manual fallback. All parsing tests mock
responses; no model was invoked.

Original release backup preserved unchanged. Separate current-frontend backup:
`/private/tmp/spry-ui-discovery-dfa14cc049/pre-publish-backup`. Publication used assets-first/index-last without --delete. All previous
object keys and unrelated object ETags preserved. Existing distribution E32YSLDLU597TU
invalidation I2GU7NMYVM4CIPBUNJAYK7KGIT completed. Served HTML/CSS/JS hashes match the new production
build; correct parser/backend URLs and Cognito public settings verified in compiled JS. New visible
entry/review labels verified in that same served build; local rendered UI tests verify their placement.
No live authenticated browser interaction was performed by this run.

## User verification

Refresh the app, sign in if needed, click New meeting and use **Paste agenda / AI parser** at the
top above Title. It is also in existing meeting details. Opening the panel requires no model call.
After separately approving real inference: paste notes, Parse with AI, edit suggestions, Use reviewed
agenda, confirm meeting date/time/location, Create meeting, reopen the agenda and verify persistence.
Test ownership isolation with two existing accounts. No Bedrock call, commit or push occurred.
