# Lab 6 — local deployment preparation report

**Historical local-preparation report.** The implementation is now deployed with Gemini 3.5 and
an authenticated real parse is verified. Use [final-report.md](final-report.md) for current status;
the dated sections below describe earlier work and are not the final acceptance record.

Updated 2026-10-29. Branch `main`, HEAD `7f3fa7b` unchanged. This phase made NO AWS API calls,
deployments, real Lambda/model invocations, IAM/profile/credential edits, shared-database queries,
shared migrations, commits or pushes. It reused the prior read-only audit findings; they were not
refreshed by contacting AWS. Local tests used mocks and a newly created disposable PostgreSQL container.

## A. Files changed in this phase

Modified (including previously untracked Lab 6 files that already existed):

- `.env.example`
- `Makefile`
- `Makefile.ai`
- `README.md`
- `backend/app/ai/agenda_lambda.py`
- `backend/app/config.py`
- `backend/app/reports/lambda_handler.py`
- `backend/app/reports/mailer.py`
- `backend/app/reports/weekly.py`
- `backend/tests/test_agenda_lambda.py`
- `front/src/components/AgendaDialog.tsx`
- `front/src/test/AgendaDialog.test.tsx`
- `infra/ai.yml`
- `infra/scripts/ai-deploy.sh`
- `docs/adr/0006-llm-agenda-parsing.md`
- `docs/lab6-architecture.md`
- `docs/lab6-migrations.md`
- `docs/lab6/deployment-and-submission.md`
- `docs/lab6/implementation-report.md`

Created:

- `backend/app/diagnostics/__init__.py`
- `backend/app/diagnostics/db_inspection.py`
- `backend/tests/test_db_inspection.py`
- `backend/tests/test_deployment_safety.py`
- `infra/scripts/aws-target.sh`
- `infra/scripts/db-inspect.sh`
- `infra/scripts/frontend-backup.sh`
- `docs/lab6/database-inspection.md`
- `docs/lab6/release-runbook.md`

The three report-module edits are style-only (format/import/newline/UTC alias) to clear the
pre-existing non-migration Ruff findings; report behavior was not redesigned. Historical migration
`5d5e3ded4830`, the forward revision and unapplied-only patch were NOT edited.

## B. CloudFormation and release blockers resolved locally

- Parser concurrency parameter now defaults to 0, meaning AWS::NoValue / reservation omitted.
  It does NOT set the Lambda concurrency to zero. Optional positive values are guarded by a
  read-only available-quota check before preview creation; the known 10-concurrency account uses 0.
- Existing `/aws/lambda/meetings-agenda-parser` is referenced by name. No LogGroup resource/import/
  deletion or retention-policy update is requested. Existing events and retention are preserved.
- Existing `meetings-monthly-5usd` budget is referenced and preflight-checked. No budget resource
  is created, adopted, replaced or deleted, and existing subscribers/thresholds remain untouched.
- Parser image tags resolve to immutable digests; actual registry image architecture is checked.
  The intended new shared image is ARM64; current x86_64 parser must update image+architecture
  in the reviewed change set, with the existing function and URL retained.
- Explicit cloud environment sets real Nova Micro and PARSER_MOCK=0. No DB settings are copied;
  imports may construct a SQLAlchemy engine via auth, but no database connection/query is needed.
- Authenticated local mock mode is restored, visibly labelled in response/title/model/UI/logs;
  zero token usage/cost; no Bedrock call. It never bypasses JWT/input/length checks and is not
  submitted as real evidence. The exact contract, versioned prompt, normal save API and ownership
  checks remain unchanged.
- Guard verifies only spry-friend / 891447916595 / us-east-1 and rejects credential overrides.
  Make defaults/export and explicit stack lookups use that profile, avoiding a default-account
  fallback after a child-process account check. No default or legacy eu-central-1 resources are used.
- Parser helper previews by default; preview creation itself still requires approval. No automatic
  failed-stack deletion. Optional AI_EXECUTE=1 is an explicit execution choice, not used here.

## C. Database inspection approach

Prepared private temporary Lambda `meetings-db-inspection-lab6`, from reviewed ARM64 image, existing
backend VPC/subnets/security group/execution role, with allowlisted DB settings. No production API
code/config/handler changes, URL, public invocation permission, new IAM policy/role, public ingress,
Data API change or permanent resource. Create/run/remove are separate script modes and approvals.

Handler accepts one fixed operation and verifies invocation account/region/name. It does not import
Alembic, ORM or seed code. PostgreSQL startup options establish read-only transactions with query/
lock/connect timeouts and TLS. It verifies transaction_read_only, runs fixed SELECTs of version
and metadata only, then always rolls back/closes. No arbitrary SQL, row contents, commits, DDL/DML
or error/credential logging. Protected local files for copying configuration are removed on exit.

Temporary Lambda uses the existing application DB login, not a newly provisioned read-only DB user;
fixed SQL and server-enforced transaction controls are explicit. Invocation can wake Aurora and
incur ordinary runtime/database costs, so no invocation was attempted. The script cleans up only
a tagged temporary function when explicitly run in remove mode. Its own optional log-group cleanup
is documented separately; shared parser/backend logs, role, VPC, SG and database are never deleted.

Instructions: [database-inspection.md](database-inspection.md). The real target's migration revision
remains UNKNOWN; fake fixtures and old image dates are not evidence of production migration state.

## D. Migration scenarios

See [full matrix](../lab6-migrations.md). Missing/empty/unknown/multiple version rows require
provenance review, not initialization/stamping. At 0003, only proven globally-unapplied historical
code may use the prepared unapplied-only patch; otherwise review a compatibility strategy. At
5d5e3ded4830, distinguish absent/compatible/incompatible agendas and rehearse the suitable forward
path without rewriting history. At 0004 with matching schema no agenda migration is needed. All
contradictory revision/schema states stop for drift investigation. Review types, nullability, PKs,
FK cascade behavior and provenance before transforming existing data. No scenario was selected.

## E. Actual local validation results

Python checks used the existing temporary Python 3.14 virtual environment; Lambda targets 3.12.
A full Lambda container build/live cold-start test remains future verification.

| Check | Result |
|---|---|
| `python -B -m pytest backend/tests -q --tb=short`, default isolated SQLite | 90 passed, 4 PostgreSQL-only skipped |
| Same command, explicitly configured new localhost:55437 disposable PostgreSQL | 94 passed, 0 failures |
| `cd front && npm test` | 39 passed / 5 files |
| `cd front && npm run build` | passed (TypeScript + Vite), existing >500 kB bundle warning |
| `cd front && npm run lint` | passed |
| `cd front && npm run format:check` | passed |
| `ruff check backend/app backend/tests backend/scripts` | passed |
| `ruff format --check backend/app backend/tests backend/scripts` | passed |
| `ruff check backend` | 2 findings only in preserved historical migration: I001 and undefined postgresql F821 |
| `ruff format --check backend` | 1 unformatted file only: preserved historical migration |
| `cfn-lint infra/*.yaml infra/*.yml` | passed / all 7 templates |
| `for script in infra/scripts/*.sh; do bash -n "$script" || exit; done` | passed |
| `git diff --check` | passed |

Exact Python executable used: `/private/tmp/spry-lab6-venv/bin/python`; Ruff/cfn-lint from the same
virtual environment. PostgreSQL tests used only the newly created local Docker container
`spry-lab6-prep-readonly-test`, no persistent volumes, explicitly named disposable databases.
The real PostgreSQL test proved CREATE TABLE is rejected inside the inspector connection, then
read-only schema inspection succeeds. TLS was disabled ONLY in this localhost test connector
because that disposable server has no TLS; production still enforces sslmode=require.
The forward migration was exercised only in rollback-only test schemas in the disposable server.

Deployment-script tests use fake AWS/Docker executables and validate wrong account/profile/override
refusal, digest pinning/architecture checks, default change-set preview, low-quota refusal, DB-env
exclusion and temporary inspector ownership checks. Fake create/invoke/delete commands do not
contact AWS. No real model outputs, deployed measurements or live inspection results are claimed.
The disposable PostgreSQL container was stopped/removed after testing; no fixture data was retained.

## F. Remaining blockers

- Actual Aurora alembic_version and metadata still need approved private inspection.
- Evidence-backed migration selection/repair/rehearsal remains required; the historical revision
  is preserved, so full backend style CI and a fresh upgrade remain blocked by it.
- New image build/push and live change-set previews have not been performed; actual architecture
  transition and no-replacement plan must be reviewed before execution.
- Instructor approval for Nova instead of originally required Claude remains outstanding.
- Real inference, deployed UI/ownership checks, evaluation table, CloudWatch event and recording
  remain outstanding. The prior audit's Nova availability metadata is not an inference test.
- Back up frontend before publishing: current bucket has no versioning. Budget is an alert, not
  a hard cap; no reservation/per-user limiter is claimed when the quota prevents reservation.

## G. Exact next actions requiring approval

Follow [release-runbook.md](release-runbook.md):

1. Guarded account re-verification and build/push one reviewed explicitly tagged ARM64 image.
2. Create the private inspector from a digest (no production function update); separately invoke
   it once, review metadata, then separately remove it and optionally only its own log group.
3. Select/approve the migration strategy from actual evidence and rehearse on a disposable copy.
4. Create backend/parser change-set previews; review no DB/network/URL/Cognito/log/budget deletion.
5. Approve execution, any specific migration, and frontend backup/publish separately.
6. Approve minimal paid Nova verification and subsequent submission evidence collection.

No aggregate deployment, blind stamp/reset, shared migration or cleanup is authorized by these
prepared commands alone. Rollback restores previous images/config/arch and archived frontend
assets while keeping existing/new agenda data; it never downgrades/drops a database.


## Final migration/release preparation

Target evidence: revision 0003, agendas absent. The historical correction remains an unapplied
review patch pending approval, retaining the revision graph. Strengthened the forward migration's
existing-schema type/nullability/FK validation. Added a reproducible local-only disposable PostgreSQL
rehearsal with seeded users, owned and ownerless meetings, participant/link and exact row fingerprints.
Observed-state upgrade and repeat-upgrade preservation passed; all five PostgreSQL migration cases
passed. Backend suite: 97 passed, 6 skipped in the default SQLite run (the five PostgreSQL migration
cases were run separately). Python lint/changed-file format, CloudFormation lint and whitespace
checks passed. No frontend code changed in this preparation; prior frontend checks are not rerun.
The disposable container/volumes were removed. No AWS calls, snapshots, application deployment,
production migrations, real model calls or Git writes were performed in this preparation.
See [final release commands](final-release-plan.md), including snapshot cost assumptions, migration
source approval, backend-before-migration dependency, review gates and data-preserving rollback.


## Controlled production deployment completed

Backend/parser reviewed change sets reached UPDATE_COMPLETE; independent private DB checks verified
0003 baseline, then head 0004_reviewed_agendas and unchanged application-table fingerprints. Frontend
published without deletion; endpoints/auth/CORS/served assets and bounded CloudWatch scans passed.
See [deployment report](deployment-report.md) and deployed-schema.json. No real Nova evaluation,
Git commit or push occurred. Real usage/log/evaluation/video evidence remains to be collected.
