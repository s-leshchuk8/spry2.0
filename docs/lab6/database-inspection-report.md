# Authorized diagnostic inspection result

Account `891447916595`, profile `spry-friend`, region `us-east-1`; identity `spry-lab`.
Target: private Aurora cluster `meetings-db`, database `meetings`.

## Observed database state

One invocation succeeded with transaction_read_only=on. Recorded revision: **0003**.
`public.agendas` is absent. `meetings` has UUID `id` primary key, nullable UUID `owner_id`
with validated FK to `users(id) ON DELETE CASCADE`, title/description/call_link/place,
created_at/updated_at, starts_at/ends_at. See the adjacent sanitized JSON metadata snapshot.
No application row contents were fetched. No migration or production write was executed.

The recorded revision is before `5d5e3ded4830`; it is not currently recorded as applied.
This does not establish whether it was ever applied/stamped and later reverted, nor its status
in other environments. The historical source remains unchanged and is still broken: missing
`postgresql` import and no predecessor creation of `agendas`.

## Connection and root-cause assessment

Verified database endpoint/port/name match the backend; password-based configuration is complete,
Aurora IAM authentication is disabled, backend ARM64 architecture and existing execution role match.
Verified existing VPC/subnets/security group and database ingress from that group. No network or
IAM changes were made. Driver wheels were reused from the reviewed Linux ARM64 Python 3.12 package.
TLS and fixed read-only startup settings succeeded. The inspector uses direct psycopg keyword
arguments; it imports no SQLAlchemy engine and triggers no application initialization or migrations.

The previous OperationalError root cause is **not established**. Successful connectivity now does
not prove whether the earlier error was transient, authentication-related, or caused by cold Aurora.
No password, raw exception, connection string or SQL parameter is included in the evidence.

## Temporary resource lifecycle

Function: `arn:aws:lambda:us-east-1:891447916595:function:meetings-db-diagnostic-e77ee244d170`.
Exactly one invocation; no retries or additional diagnostic functions. Used a ZIP package rather
than pushing an ECR image. The unique function and explicitly tagged unique log group were
ownership/code-hash verified before deletion and verified absent afterward. Existing backend and
parser RevisionId, CodeSha256 and LastModified remained unchanged. No temporary AWS resources remain.

## Migration decision and rehearsal

Smallest candidate **if history permits repair of the unused historical revision**: apply the
prepared `docs/migration-repairs/unapplied-only.patch`, which imports the PostgreSQL dialect and
creates the missing agenda table; then run the normal chain through `0004_reviewed_agendas`.
Do not apply this candidate to shared environments until its history condition is established.
If another environment used the revision, prepare a separately reviewed compatibility/bootstrap
and version reconciliation plan; never blindly stamp past the broken revision or drop existing data.

Local PostgreSQL 16 rehearsal: 3 forward-revision tests passed. Applied the candidate patch only in
a temporary source copy and successfully upgraded an empty disposable database through the entire
chain to `0004_reviewed_agendas`, with `meeting_id`, `final_agenda`, `ai_suggestion` columns.
The PostgreSQL container and its volumes were removed. This proves candidate fresh-chain execution,
not production data compatibility or cross-environment history. No repository migration was changed.

## Release gate and next actions

Deployment remains blocked pending historical-repair decision, approved DB backup and migration plan.
Keep old frontend until schema/API compatibility is verified. Follow `release-runbook.md` for a unique
release tag, ARM64 backend/parser image build and digest verification, frontend asset backup, change-set
previews and data-preserving image/frontend rollback. No change sets, image pushes, release deployments,
backups of cloud data or Bedrock calls were executed during this diagnostic run.

After explicit approval: confirm migration history scope; adopt/rehearse the selected plan on a
backup/restored copy as needed; back up Aurora; build/push release images; preview and inspect the
backend/parser change sets (parser image and architecture must change together); approve application
updates and migration separately; verify ordinary CRUD and ownership; back up/publish frontend;
approve real Nova evaluation and collect five cases, CloudWatch evidence and the submission recording.
Instructor approval remains required for the Nova substitution for Claude.
