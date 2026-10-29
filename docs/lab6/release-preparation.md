# Controlled release preparation — published image and unexecuted previews

**Current status:** reviewed backend/parser change sets executed, migration verified at
0004_reviewed_agendas, frontend published and bounded smoke checks passed. See
[deployment-report.md](deployment-report.md). Earlier preparation/approval wording below records
prior stages; do not repeat completed operations. Real Bedrock evaluation and Git writes remain pending.

Release `lab6-nova-20261029t182318z-cf9bc2e1`; verified profile `spry-friend`, account `891447916595`, user
`spry-lab`, region `us-east-1`. No snapshot, frontend backup, build or migration rehearsal was repeated.

## ECR lifecycle

Repository `meetings-backend`, CloudFormation owner `meetings-backend-ecr`, logical resource
`BackendRepository`. The authorized ECR API update changed only `countNumber: 5` to `10`.
Rule priority 1, tagStatus any, countType imageCountMoreThan and action expire are unchanged.
The original descriptive label still says last 5; the functional retention value is 10.
The lifecycle preview completed with **zero expiring images**. All five prior image digests remain
available after publishing (six images total). No image deletion was requested.

Before policy: `/private/tmp/spry-release-lab6-nova-20261029t182318z-cf9bc2e1/retention-f11030a7/before.json`; after: `/private/tmp/spry-release-lab6-nova-20261029t182318z-cf9bc2e1/retention-f11030a7/after.json`;
preview: `/private/tmp/spry-release-lab6-nova-20261029t182318z-cf9bc2e1/retention-f11030a7/preview.json`; previous owning-stack template is preserved alongside these files.
`infra/backend-ecr.yaml` now uses count 10 locally. Because CloudFormation execution is prohibited,
the live ECR API change is not yet reflected in the stored owning-stack template: known temporary
drift. Reconcile that template in a separately reviewed future ECR-stack update before using the
old stack deployment path, or it could restore count 5. No ECR stack update was executed here.

## Published release

Tag: `891447916595.dkr.ecr.us-east-1.amazonaws.com/meetings-backend:lab6-nova-20261029t182318z-cf9bc2e1`.
Verified immutable registry URI:
`891447916595.dkr.ecr.us-east-1.amazonaws.com/meetings-backend@sha256:5641619e538ae30a6f1ca21909998236841ef05ca54623e654da2c25272d0782`.
Architecture: Linux ARM64. Registry digest matches the previously built local manifest exactly.
Both backend and parser use this same reviewed image with their respective handler commands.
A network timeout interrupted one layer upload; resuming the same content-addressed tag succeeded
without rebuild. Isolated temporary Docker login credentials were removed afterward.

## Backend preview

ARN: `arn:aws:cloudformation:us-east-1:891447916595:changeSet/preview-lab6-nova-20261029t182318z-cf9bc2e1-api/8675094c-e776-4d66-865a-53a434cf3cd6`.
Status CREATE_COMPLETE, execution AVAILABLE; **not executed**.
One resource: BackendFunction, Modify Code, Replacement=False. No database, network, Cognito,
IAM, frontend, budget or log resources change. Existing parameter values retained, Seed=false.

## Parser preview

ARN: `arn:aws:cloudformation:us-east-1:891447916595:changeSet/preview-lab6-nova-20261029t182318z-cf9bc2e1-parser/7a0b1d9a-d9f1-44fd-935d-9fa640547349`.
Status CREATE_COMPLETE, execution AVAILABLE; **not executed**.

- AgendaParserFunction: Modify, Replacement=False. New image, x86_64 -> arm64, explicit public
  configuration allowlist, Nova Micro Converse, `PARSER_MOCK=0`, prompt agenda-v1; remove copied DB
  environment variables; reference existing CloudWatch group. No VPC configuration or reservation.
- AgendaParserRole: Modify, Replacement=False. Same trust and logging managed policy. Remove broad
  `bedrock-mantle:CreateInference`, wildcard InvokeModel and streaming access. Permit only
  non-streaming `bedrock:InvokeModel` for the Nova Micro US inference profile and Micro foundation
  model through that profile. This is a narrowing of existing permissions, not unintended expansion.
- AgendaParserUrl: Modify, **Replacement=Conditional**. The sole detail is Dynamic evaluation of
  TargetFunctionArn caused by AgendaParserFunction.Arn (a property that requires recreation if its
  value actually changes). Existing/proposed URL definitions and named function are identical,
  ProjectName remains meetings, and function Replacement=False. No actual target ARN change is
  expected, but this is a formal conditional marker, not a guarantee of Replacement=False. Review
  and accept this dependency evidence before execution; stop if a later preview changes it.

Existing parser/backend Cognito and CORS values were verified equal and are retained in proposed
parameters. No Cognito resources, permissions, budgets or log groups are added, removed or replaced.
Existing meetings-monthly-5usd remains externally managed. There are no Remove actions or unconditional
replacements in either change set. Production backend/parser RevisionId, CodeSha256, LastModified
and architecture were verified unchanged after preview creation.

Full change-set details and parameter evidence are private files in `/private/tmp/spry-release-lab6-nova-20261029t182318z-cf9bc2e1`.

## Existing recovery evidence retained

Snapshot `meetings-pre-lab6-nova-20261029t182318z-cf9bc2e1` remains the completed backup from the prior run; no new one was made.
Frontend backup remains `/private/tmp/spry-release-lab6-nova-20261029t182318z-cf9bc2e1/frontend-backup`; never overwrite it. Retain a durable private copy
before publishing, because /private/tmp is temporary storage.

## Next separately approved actions — NOT executed

1. Review/accept the conditional URL marker and known ECR stack-template drift. Confirm no concurrent
   source/configuration changes have invalidated these exact previews. Preserve the release image.
2. Execute the exact backend change set, wait for stack completion and verify the deployed digest,
   ARM64 architecture, Seed=false and ordinary meeting CRUD.
3. Invoke the existing private migration action once, then independently verify head 0004 and the
   agenda schema through the approved private inspection path. No blind stamp/downgrade/reset.
4. Execute the exact parser change set, wait and verify same URL/Cognito, real Nova config and no DB
   credentials. Then approve frontend publication from the existing verified backup/release source.
5. Separately approve real Nova verification/evaluation, collect CloudWatch evidence and recording,
   then approve Git commit/push. Instructor approval for the Nova-vs-Claude deviation remains needed.

Prepared commands below require explicit execution/migration approval:

```bash
export AWS_PROFILE=spry-friend AWS_REGION=us-east-1
source infra/scripts/aws-target.sh
aws_target_init
aws_spry cloudformation execute-change-set --change-set-name 'arn:aws:cloudformation:us-east-1:891447916595:changeSet/preview-lab6-nova-20261029t182318z-cf9bc2e1-api/8675094c-e776-4d66-865a-53a434cf3cd6'
aws_spry cloudformation wait stack-update-complete --stack-name meetings-backend
# Verify digest/architecture/Seed=false and CRUD before the separately approved migration.
umask 077
AWS_MAX_ATTEMPTS=1 aws_spry lambda invoke --function-name meetings-backend \
  --cli-binary-format raw-in-base64-out --payload '{"action":"migrate"}' \
  --cli-read-timeout 75 '/private/tmp/spry-release-lab6-nova-20261029t182318z-cf9bc2e1/migration-result.json'
# Require no FunctionError and status=migrated; independently inspect actual revision/schema.
# Only after successful migration verification and parser-execution approval:
aws_spry cloudformation execute-change-set --change-set-name 'arn:aws:cloudformation:us-east-1:891447916595:changeSet/preview-lab6-nova-20261029t182318z-cf9bc2e1-parser/7a0b1d9a-d9f1-44fd-935d-9fa640547349'
aws_spry cloudformation wait stack-update-complete --stack-name meetings-ai
# Frontend publish and paid verification remain separately gated in final-release-plan.md.
```

No production migration, change-set execution, frontend publish, Bedrock invocation, database
modification, existing-resource deletion, Git commit or push occurred in this run.
