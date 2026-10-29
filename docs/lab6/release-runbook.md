# Minimal release plan — commands prepared, NOT executed

**Local Gemini candidate:** see [gemini-replacement.md](gemini-replacement.md). Gemini 3.5 Flash-Lite
and agenda-v2-gemini are prepared locally. The user reports one successful real structured-output
probe; no Gemini AWS deployment has occurred. See [release plan](gemini-release-plan.md).
Earlier Nova deployment/evaluation entries below are historical. Keep all real-result cells pending.

**Current status:** reviewed backend/parser change sets executed, migration verified at
0004_reviewed_agendas, frontend published and bounded smoke checks passed. See
[deployment-report.md](deployment-report.md). Earlier preparation/approval wording below records
prior stages; do not repeat completed operations. Real Bedrock evaluation and Git writes remain pending.

Current evidence-backed sequence: [final-release-plan.md](final-release-plan.md). It supersedes
the earlier unknown-revision gate below: target revision is 0003 with no agendas. Historical repair
remains a separately approved source correction; snapshot and all production actions remain unexecuted.

All AWS writes, image pushes, Lambda creation/invocation/removal, migrations, inference and frontend
publishing require explicit approval. No `aws-deploy` aggregate target: it can alter Google Cognito
settings and invoke migrations. Leave all eu-central-1 legacy `spry` resources untouched.

## 1. Target and one release tag

Before any AWS operation, source the guard. It rejects credential overrides, wrong profile/region,
and wrong STS account before any other call. It never overwrites a profile or credentials.

```bash
source infra/scripts/aws-target.sh
aws_target_init
RELEASE_TAG="lab6-nova-$(date -u +%Y%m%dT%H%M%SZ)"
REPOSITORY=891447916595.dkr.ecr.us-east-1.amazonaws.com/meetings-backend
```

Keep these values for the entire release. Do not use `latest` as a release/rollback reference.
Keep `.env` credential-free. Record STS identity and the prior backend/parser digests and architectures.

## 2. Build and push only (no application update or migrations)

The existing API is ARM64 and the parser is x86_64. The new reviewed shared image will be ARM64;
the parser change set must update both architecture and image together. The Dockerfile/handler
source is shared; no extra repository or provider abstraction is needed.

```bash
aws_spry ecr get-login-password | docker login --username AWS --password-stdin \
  891447916595.dkr.ecr.us-east-1.amazonaws.com
# Build locally; no AWS resource update:
docker buildx build --platform linux/arm64 --provenance=false --load \
  -f backend/Dockerfile.lambda -t "$REPOSITORY:$RELEASE_TAG" backend
# Image push is an AWS WRITE; run only with approval:
docker push "$REPOSITORY:$RELEASE_TAG"
DIGEST=$(aws_spry ecr describe-images --repository-name meetings-backend \
  --image-ids "imageTag=$RELEASE_TAG" --query 'imageDetails[0].imageDigest' --output text)
IMAGE_URI="$REPOSITORY@$DIGEST"
docker buildx imagetools inspect "$IMAGE_URI" --format '{{json .Image}}'
```

Verify `architecture=arm64`, `os=linux`. The parser preview script independently inspects this
registry config and refuses a mismatch; tag inputs are resolved to immutable digests first.
Archive prior image artifacts or otherwise protect them from the repository's five-image lifecycle
before pushing enough releases to expire them. Docker credentials must come from the guarded login.

## 3. Database evidence first

Use `database-inspection.md` to prepare/create/invoke/remove the private temporary inspector, with
separate approvals. Do not update the backend code merely to gain an inspection endpoint. Review
`../lab6-migrations.md`, choose a plan only from actual evidence, back up appropriately, then rehearse
that exact plan on disposable PostgreSQL. Historical migration is untouched in this local phase.

## 4. Preview backend and parser changes

Creating a change set is itself an AWS write requiring approval, even without execution.

```bash
aws_spry cloudformation deploy --stack-name meetings-backend --template-file infra/backend.yaml \
  --capabilities CAPABILITY_IAM --no-execute-changeset --no-fail-on-empty-changeset \
  --parameter-overrides "ImageUri=$IMAGE_URI" Architecture=arm64

AWS_PROFILE=spry-friend AWS_REGION=us-east-1 AI_IMAGE_URI="$IMAGE_URI" \
AI_LAMBDA_ARCH=arm64 PARSER_MODEL=us.amazon.nova-micro-v1:0 PARSER_CONCURRENCY=0 \
  bash infra/scripts/ai-deploy.sh
```

The parser script previews by default. `AI_EXECUTE=1` explicitly opts into execution; do not set it
before approval. Prefer executing the reviewed change-set ARN rather than generating a new plan.

Review: no DB/network/Cognito replacement or deletion; same function names and URLs; parser
architecture/image update; model-scoped InvokeModel; `PARSER_MOCK=0`; no parser DB credentials;
no reserved-concurrency property; existing log-group reference; no new budget/log group. Backend
parameters omitted from the preview retain prior values. Inspect the actual change set rather
than assuming omission is safe if templates/parameters later change.

The existing log group is not imported, recreated or deleted; its existing events and current
retention policy are preserved. The pre-existing `meetings-monthly-5usd` budget remains externally
managed with the existing email/thresholds. This stack merely outputs its name. Check subscribers
before release; do not create a second budget. Setting log retention could remove older events,
so it is a separate decision, not silently included in this release.

Only after approvals:

```bash
aws_spry cloudformation execute-change-set --change-set-name "$APPROVED_BACKEND_CHANGE_SET_ARN"
# Wait for backend update; apply only the evidence-backed, rehearsed migration plan.
# No generic migration command is supplied until the actual revision is known.
aws_spry cloudformation execute-change-set --change-set-name "$APPROVED_PARSER_CHANGE_SET_ARN"
```

Do not expose the new frontend until migration/application compatibility is confirmed. If updating
the backend image is needed to run approved migrations, keep the old frontend until completion;
verify ordinary meeting CRUD and stop/roll back the image if migration fails. Parser environment is
replaced with an explicit allowlist, removing the old mock and copied DB variables. Its imports
construct no DB connections, and it never needs database credentials.

## 5. Back up frontend BEFORE publishing

The current frontend bucket has no versioning. Retain a verified local copy before `s3 sync --delete`.

```bash
BACKUP_DIR="/private/tmp/spry-release-backup-$RELEASE_TAG"
AWS_PROFILE=spry-friend AWS_REGION=us-east-1 \
  bash infra/scripts/frontend-backup.sh "$BACKUP_DIR"
```

This reads S3 and image/template metadata only; it creates a private local folder with index.html,
all assets, checksums, prior image references and the old parser template. It does not back up
application rows or substitute for an approved DB backup. Copy the backup to a durable private
location; `/private/tmp` is not permanent storage. Inspect it before publishing.

With separate publishing approval (Cognito/URL values come from existing stacks):

```bash
make AWS_PROFILE=spry-friend AWS_REGION=us-east-1 PROJECT=meetings aws-frontend-publish
```

Do not use the legacy `deploy-frontend` target; it points at another S3 bucket. No Cognito/frontend
stack rebuild is needed solely to publish the new SPA. Do not delete/replace old Google settings.

## 6. Minimal real Nova verification (paid, separate approval)

Sign into the deployed meetings app using an existing account. Paste the Ukrainian example and
parse once. Confirm response model `us.amazon.nova-micro-v1:0`, prompt `agenda-v1`, no mock marker,
nonzero usage in the matching log, sensible editable fields, one correction and explicit Save.
Reopen to verify final agenda and original suggestion. Confirm a second user cannot access it.
Then collect all five real evaluation cases, one actual CloudWatch log line and ≤45-second recording.
Do not fabricate results from local mocks. Instructor approval for the Nova deviation remains needed.

Local mock: `PARSER_MOCK=1` in a locally run parser handler returns a fixed visibly MOCK suggestion,
model `mock`, tokens/cost zero; it still checks JWT and input length. CloudFormation always sets 0.
The frontend also shows a persistent mock warning. Do not deploy a mock as real model evidence.

## 7. Rollback while preserving data

- Preserve the previous image digests/architectures and frontend backup before release.
- Restore the prior API image if necessary; new agenda tables/data stay intact. Never downgrade,
  drop, stamp, reset or destroy a database as application rollback.
- If a parser release fails, disable the new parse UI / restore old frontend and keep manual entry.
  Reverting parser code requires matching its former x86_64 architecture and compatible public
  Cognito/model settings; do not restore copied DB secrets or present the old mock as real inference.
- Review stack rollback for function/image/architecture changes only; existing VPC/DB/URLs/Cognito,
  log events and budget must remain. Do not recover a failed stack by automatic deletion.
- Restore frontend assets first, then index.html; avoid deleting potentially needed release assets:

```bash
# AWS WRITES — require explicit rollback approval and a verified backup.
aws_spry s3 sync "$BACKUP_DIR/site" s3://meetings-frontend-sitebucket-la6ugmfuat3e \
  --exclude index.html --cache-control 'public,max-age=31536000,immutable'
aws_spry s3 cp "$BACKUP_DIR/site/index.html" \
  s3://meetings-frontend-sitebucket-la6ugmfuat3e/index.html --cache-control no-cache
aws_spry cloudfront create-invalidation --distribution-id E32YSLDLU597TU --paths '/*'
```

Rollback permission does not authorize unrelated IAM/profile/database changes. Temporary inspection
cleanup is separately scoped to the tagged inspector and its own optional log group.
