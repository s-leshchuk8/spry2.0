# Evidence-backed migration and release plan

**Current status:** reviewed backend/parser change sets executed, migration verified at
0004_reviewed_agendas, frontend published and bounded smoke checks passed. See
[deployment-report.md](deployment-report.md). Earlier preparation/approval wording below records
prior stages; do not repeat completed operations. Real Bedrock evaluation and Git writes remain pending.

Current preparation: historical correction applied locally; rehearsal passed; snapshot/frontend backup
complete; image published; backend/parser change sets available but unexecuted. Do not rerun completed
steps below; use the exact current ARNs and conditional-URL review in release-preparation.md. Snapshot/image/preview outcomes are recorded separately in `release-preparation.md`.
Production migrations, change-set execution, frontend publication and model invocation remain unapproved.

Scope: `spry-friend`, account `891447916595`, `us-east-1`, project `meetings`.
Snapshot, retention increase and image publication are complete. Production migrations, change-set
execution, frontend publication, paid inference, commit and push remain unapproved.
The only database writes performed in this preparation are in a new disposable local PostgreSQL.

## Decision

Observed: `0003`, no public agendas; meetings UUID PK and owner FK are present. Recommend the
small correction already captured in `../migration-repairs/unapplied-only.patch`: import the
PostgreSQL dialect, create the missing agenda table if absent, add the suggestion only if absent.
Retain revision IDs and dependency chain. Then execute normal Alembic upgrade to the explicit
`0004_reviewed_agendas` target. No stamp, reset, downgrade, data rewrite or new revision branch.

A forward revision alone cannot solve this: Alembic must first execute the broken predecessor.
For this inspected target the corrected path is additive, and the normal PostgreSQL Alembic
transaction covers the pending revisions. Already-recorded predecessors in other databases are
skipped by Alembic. However, their schema may differ; a recorded revision cannot prove its exact
execution history. Historical code correction must be explicitly approved as such, not represented
as a newly appended migration. If historical file changes are prohibited by another deployment's
policy, stop and design a separately reviewed compatibility path instead of bypassing with stamp.
The patch was subsequently approved and applied locally, with IDs and dependencies retained. Its old filename reflects
its original conservative gate; do not apply it blindly across other environments.

The forward revision now rejects wrong UUID/JSON/JSONB types, nullability, primary key, or missing
cascade meeting FK. It does not transform incompatible data. Extra columns are preserved.
The primary key supplies the only required agenda index; no duplicate meeting_id index is needed.

## Rehearsal

Run from repo root using the backend's installed development environment:

```bash
python backend/scripts/rehearse_lab6_migration.py
```

Requires a pre-existing local `postgres:16-alpine` image and Docker. It creates only a unique
labelled localhost PostgreSQL container, copies migrations into a temporary directory, applies the
candidate patch there, upgrades to 0003, inserts synthetic users, owned/ownerless meetings,
participant/link, then upgrades to 0004. It checks complete existing row fingerprints, agenda
UUID/JSON/JSONB/nullability, FK/cascade, PK uniqueness, one index, repeat upgrade and saved-agenda
preservation. It removes only its own container and anonymous volumes, including after failure.
The repository historical migration remains untouched. This is not a restored production copy;
users/participants metadata not fetched by the inspector is reproduced from revisions 0001–0003.
Production row values, row counts, triggers and unrelated objects were not copied or inspected.

## Commands for the separately approved release

Use Bash from repo root, execute stage by stage, inspect each result; do not paste as one unattended
script. Stop on any failure. Do not automatically recreate stacks, rerun migrations, or switch accounts.

### 0. Approve the source correction and freeze release contents

These local source commands are proposed, not executed by this preparation:

```bash
set -euo pipefail
export AWS_PROFILE=spry-friend AWS_REGION=us-east-1
source infra/scripts/aws-target.sh
aws_target_init
RELEASE_TAG="lab6-nova-$(date -u +%Y%m%dT%H%M%SZ)-$(python3 -c 'import uuid; print(uuid.uuid4().hex[:8])')"
SNAPSHOT_ID="meetings-pre-${RELEASE_TAG}"
REPOSITORY=891447916595.dkr.ecr.us-east-1.amazonaws.com/meetings-backend
# Only after approval to correct historical source:
git apply --check docs/migration-repairs/unapplied-only.patch
git apply docs/migration-repairs/unapplied-only.patch
python backend/scripts/rehearse_lab6_migration.py
python -m pytest backend/tests -q
```

The rehearsal applies the patch to its own copy and therefore supports applying the
patch to the repository: it detects already-repaired source and skips patching that copy. Do not
change release source after image build without a new tag/build and another relevant verification.

### 1. Aurora backup — CREATE not yet authorized

No snapshot has been created by this preparation. Use the same unique identifier throughout.
Verify cluster ARN/account/engine/database before snapshot creation. Use a planned quiet window:
a snapshot preserves its own point in time, not later writes. Avoid schema changes during release.

```bash
aws_target_init
aws_spry rds describe-db-clusters --db-cluster-identifier meetings-db \
  --query 'DBClusters[0].{ARN:DBClusterArn,DB:DatabaseName,Engine:Engine,Status:Status}'
# Require account 891447916595, database meetings, engine aurora-postgresql, status available.
aws_spry rds create-db-cluster-snapshot --db-cluster-identifier meetings-db \
  --db-cluster-snapshot-identifier "$SNAPSHOT_ID" \
  --tags Key=PROJECT_NAME,Value=meetings Key=PURPOSE,Value=lab6-pre-migration
aws_spry rds wait db-cluster-snapshot-available --db-cluster-snapshot-identifier "$SNAPSHOT_ID"
aws_spry rds describe-db-cluster-snapshots --db-cluster-snapshot-identifier "$SNAPSHOT_ID" \
  --query 'DBClusterSnapshots[0].{ARN:DBClusterSnapshotArn,Cluster:DBClusterIdentifier,Status:Status,Created:SnapshotCreateTime,Encrypted:StorageEncrypted}'
```

Require the exact source cluster and snapshot status available; record ARN/time privately.
Manual snapshots persist until explicitly removed. No automatic snapshot cleanup is included.
Aurora backup storage can incur additional GB-month charges above the free allowance; total existing
backup usage, changed blocks and retention determine the incremental charge. Do not promise this
snapshot costs zero. Estimate `billable extra GB × current us-east-1 backup rate × retained days/30`;
for illustration only, 1 extra GB at an assumed $0.021/GB-month for 7 days is about $0.005.
The rate is an assumption, not a verified account quote. Check current pricing and existing usage.
Restoring/rehearsing an AWS copy would add cluster instance/ACU/storage charges and needs approval.
Sources: [Aurora backup storage](https://docs.aws.amazon.com/AmazonRDS/latest/AuroraUserGuide/aurora-storage-backup.html),
[Aurora pricing](https://aws.amazon.com/rds/aurora/pricing/).

### 2. Stage release image and preview backend (migration prerequisite)

The current backend image predates the migration repair. The existing migration execution path is
its private IAM-authenticated Lambda invocation. Therefore the smallest plan **builds and updates
the backend before invoking migrations**, while keeping the old frontend. Running the migration
before installing its code would instead require another temporary VPC migration Lambda; that
extra resource is unnecessary for this additive schema change and is not prepared here.

Back up frontend/prior immutable image references now, before any Lambda update:

```bash
BACKUP_DIR="$HOME/spry-release-backups/$RELEASE_TAG"
mkdir -p "$HOME/spry-release-backups"
bash infra/scripts/frontend-backup.sh "$BACKUP_DIR"
aws_spry ecr get-login-password | docker login --username AWS --password-stdin \
  891447916595.dkr.ecr.us-east-1.amazonaws.com
docker buildx build --platform linux/arm64 --provenance=false --load \
  -f backend/Dockerfile.lambda -t "$REPOSITORY:$RELEASE_TAG" backend
docker push "$REPOSITORY:$RELEASE_TAG"
DIGEST=$(aws_spry ecr describe-images --repository-name meetings-backend \
  --image-ids "imageTag=$RELEASE_TAG" --query 'imageDetails[0].imageDigest' --output text)
[[ "$DIGEST" = sha256:* ]]
IMAGE_URI="$REPOSITORY@$DIGEST"
docker buildx imagetools inspect "$IMAGE_URI" --format '{{json .Image}}'
# Require linux/arm64 and verify reviewed migration files in the built image.
aws_spry cloudformation deploy --stack-name meetings-backend --template-file infra/backend.yaml \
  --capabilities CAPABILITY_IAM --no-execute-changeset --no-fail-on-empty-changeset \
  --parameter-overrides "ImageUri=$IMAGE_URI" Architecture=arm64 Seed=false
aws_spry cloudformation list-change-sets --stack-name meetings-backend
# Copy the exact newly created ARN after inspecting name/time/status:
read -r APPROVED_BACKEND_CHANGE_SET_ARN
aws_spry cloudformation describe-change-set --change-set-name "$APPROVED_BACKEND_CHANGE_SET_ARN"
```

Review: only expected backend image/Seed changes; no DB/network/Cognito/log deletion/replacement or
unexpected configuration changes. Preserve prior image artifacts from the ECR lifecycle policy.
An empty change set is not permission to execute an unrelated old change set. Never print the full
backend environment; only queried public fields/key names are safe to display.

### 3. Approved backend update, then explicit approved migration

```bash
aws_target_init
aws_spry cloudformation execute-change-set --change-set-name "$APPROVED_BACKEND_CHANGE_SET_ARN"
aws_spry cloudformation wait stack-update-complete --stack-name meetings-backend
aws_spry lambda get-function --function-name meetings-backend \
  --query '{image:Code.ResolvedImageUri,architecture:Configuration.Architectures,seed:Configuration.Environment.Variables.SEED}'
# Require IMAGE_URI, arm64, SEED=false. Verify ordinary existing meeting CRUD before proceeding.
umask 077
MIGRATION_RESULT="$BACKUP_DIR/migration-result.json"
AWS_MAX_ATTEMPTS=1 aws_spry lambda invoke --function-name meetings-backend \
  --cli-binary-format raw-in-base64-out --payload '{"action":"migrate"}' \
  --cli-read-timeout 75 "$MIGRATION_RESULT"
python3 - "$MIGRATION_RESULT" <<'PY'
import json,sys
assert json.load(open(sys.argv[1])) == {'status':'migrated'}, 'Migration failed; stop without retry'
print('Migration handler reports success')
PY
```

This invokes the existing action, upgrades the repaired chain to its sole head (0004), and calls
seed.main, which does nothing only when SEED=false. Require no FunctionError in invocation metadata
as well as the expected payload. Do not call the aggregate Makefile deployment/migration targets.
Do not publish frontend or deploy parser after any failure; retain private error evidence, inspect
transaction outcome with a separately approved read-only path, and restore the prior backend image
if required. Do not run downgrade/stamp/reset. The normal migration path has an advisory lock;
perform no concurrent migration runs and stop if it times out. After success, approve one final
read-only inspection to confirm actual head and schema before frontend publication; handler success
alone is not independent schema evidence. Compare user/meeting counts privately through that approved
path if desired; do not expose row contents. Such a verification needs its own private execution
path and temporary-resource approval if the prior inspector procedure is reused.

### 4. Parser preview and deployment

```bash
AWS_PROFILE=spry-friend AWS_REGION=us-east-1 AI_IMAGE_URI="$IMAGE_URI" \
AI_LAMBDA_ARCH=arm64 PARSER_MODEL=us.amazon.nova-micro-v1:0 PARSER_CONCURRENCY=0 \
  bash infra/scripts/ai-deploy.sh
aws_spry cloudformation list-change-sets --stack-name meetings-ai
read -r APPROVED_PARSER_CHANGE_SET_ARN
aws_spry cloudformation describe-change-set --change-set-name "$APPROVED_PARSER_CHANGE_SET_ARN"
# Execute only after review/approval of this exact ARN:
aws_spry cloudformation execute-change-set --change-set-name "$APPROVED_PARSER_CHANGE_SET_ARN"
aws_spry cloudformation wait stack-update-complete --stack-name meetings-ai
aws_spry lambda get-function --function-name meetings-agenda-parser \
  --query '{image:Code.ResolvedImageUri,architecture:Configuration.Architectures,model:Configuration.Environment.Variables.PARSER_MODEL,mock:Configuration.Environment.Variables.PARSER_MOCK}'
```

Review the change set for expected role/model permissions and image/architecture changes, no new
budget/log group, same URL/Cognito/CORS, outside VPC, mock off, and no reserved concurrency.
Only query parser environment after confirming the reviewed template removed historical DB keys;
otherwise query a public allowlist instead. Model is Nova Micro Converse, prompt agenda-v1.

### 5. Frontend publication and rollback

The durable backup from step 2 must contain index.html, assets/checksums and old image references.
Recheck it immediately before publishing; do not overwrite it. Existing URLs/Cognito are retained.

```bash
make AWS_PROFILE=spry-friend AWS_REGION=us-east-1 PROJECT=meetings aws-frontend-publish
```

See `release-runbook.md` step 7 for exact asset/index rollback commands. Restore old frontend or
old backend image through a reviewed stack change set if needed; keep new agenda tables and data.
Reverting parser also requires its prior architecture to match the prior image. Never use schema
downgrade/drop or delete stacks for rollback. A snapshot restore creates a NEW Aurora cluster;
restore + writer creation + private endpoint cutover is an exceptional separately approved recovery,
not an in-place undo. Preserve original DB and later writes while planning reconciliation.
[Restore reference](https://docs.aws.amazon.com/AmazonRDS/latest/AuroraUserGuide/aurora-restore-snapshot.html).

### 6. Approved real Nova verification and evidence

Sign in with an existing account. Parse one Ukrainian agenda; confirm model, prompt version,
nonzero tokens, editable suggestions, explicit save, reopen persistence and manual fallback.
Verify a second user's ownership isolation. Then execute the five evaluation cases from the
existing evaluation template; capture actual output/latency/tokens/cost and one sanitized log line.
No real inference was performed during preparation. Instructor approval is required for Nova
instead of the original assignment's Claude requirement.

```bash
aws_spry logs filter-log-events --log-group-name /aws/lambda/meetings-agenda-parser \
  --filter-pattern '"agenda_parsed"' --limit 20
```

Use the exact event name emitted by the parser (check `backend/app/ai/agenda_lambda.py`) if the filter is
empty; an empty result does not justify another inference. Review output for sensitive fields
before including it in submission. Record <=45-second walkthrough and complete evaluation docs.

### 7. Final Git commit/push — separate approval

```bash
git status --short
git diff --check
git diff --stat
# Review all pre-existing modified/untracked files and secret scans before staging.
# Stage only individually reviewed project files; never git add . blindly.
git add -- <reviewed-paths>
git diff --cached --check
git diff --cached --stat
git commit -m "Complete Lab 6 agenda parsing with Nova Micro"
git push origin main
```

`<reviewed-paths>` is a required review input, not a literal shell argument. Verify current branch
and remote before push; no branch change is requested. No commit or push happened in preparation.
