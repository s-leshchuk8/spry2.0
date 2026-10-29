# Gemini 3.5 Flash-Lite release — PREPARED, NOT EXECUTED

Account spry-friend / 891447916595 / us-east-1. User-reported successful test:

```json
{"status":"validated","model":"gemini-3.5-flash-lite","items":1,"input_tokens":121,"output_tokens":88}
```

No need to repeat that probe. The default model, API client default, example/config/Makefile and
CloudFormation/deployment script now select gemini-3.5-flash-lite. Same prompt agenda-v2-gemini,
Pydantic contracts and response shape. Free-tier cost logging is an explicit project assumption;
paid estimates now use this model's standard $0.30/$2.50 per million input/output tokens.
Historical 2.5/Claude/Nova suggestion metadata remains supported by persistence tests.
No frontend, authentication, database or migration change is needed. Runtime secret reading and
production parsing remain unverified until the approved release is deployed.

## Exact expected changes (confirm in the live preview after approval)

| Resource/artifact | Intended change |
|---|---|
| Secrets Manager meetings/gemini-api-key | Create once, or add a new version only if an existing correctly owned/tagged secret exists. JSON api_key value comes only from hidden input; default AWS-managed encryption, no new KMS key. |
| Existing ECR meetings-backend repository | Push one new immutable ARM64 release image reference; no repository replacement, retention change or image deletion. Shared repository name does not imply backend Lambda deployment. |
| meetings-ai / AgendaParserFunction | Update only parser image/environment: model 3.5, prompt v2, mock off, non-secret ARN and billing assumption. Existing architecture, timeout/memory, outside-VPC placement, URL/Cognito/CORS/log group preserved; no reservation. |
| meetings-ai / AgendaParserRole | Replace obsolete Bedrock invocation permissions with secretsmanager:GetSecretValue on only the supplied exact secret ARN; retain existing logging policy/trust. No write/list permissions or broad KMS/secret access. |
| meetings-ai / AgendaParserUrl | Definition/target remains unchanged. CloudFormation may show the previously observed conditional dependency marker from function/role changes; stop on an actual target/URL replacement or any unexpected removal/replacement. |

No changes to backend Lambda, Aurora, schema/data, Cognito, S3 frontend, CloudFront, budget alerts,
existing log events or unrelated stacks. No Secrets Manager resource is created by the parser stack:
the helper manages its value separately; CloudFormation receives only its exact ARN.
Actual change-set details cannot be asserted until approval allows creating the preview.

## Expected charges

- Secrets Manager: standard $0.40 per secret/month plus $0.05 per 10,000 API calls, subject to
  prorating/credits. Warm-process retrieval cache lasts at most five minutes. No claim of zero AWS cost.
- Existing Lambda execution/CloudWatch logs and one additional ECR image retain ordinary usage/storage
  charges; no new database, NAT, permanent compute service or customer-managed KMS key.
- Google lists standard free-tier text input/output for this model. Actual project tier/limits apply;
  do not enable billing or upgrade the project/support plan. The AWS 5 USD alert does not cap Google
  spend. If switched to paid Google tier, set PARSER_BILLING_TIER=paid for honest estimates.
- No charges were incurred by a new model call, secret or image in this local preparation.

Sources: https://aws.amazon.com/secrets-manager/pricing/ and
https://ai.google.dev/gemini-api/docs/pricing.

## Secure setup — run ONLY after secret-write approval

From repository root in your own private VS Code terminal:

```bash
/private/tmp/spry-lab6-venv/bin/python backend/scripts/gemini_key.py --store-secret
```

Enter the API key using the hidden getpass prompt; never in shell arguments, .env, source, chat or
screenshots. Type `STORE SECRET IN 891447916595` only after approval to create/update the secret.
This mode performs no Gemini request. It verifies the explicit spry-friend/us-east-1 identity before
accessing Secrets Manager, rejects credential/endpoint overrides, tags/checks ownership and prints
only the resulting ARN. The API key is not persisted locally or passed through shell processes.
The default AWS-managed encryption path is required; stop for review if an existing secret uses a
custom KMS key instead of adding broad permissions. Preserve the printed ARN as non-secret config.

## Parser-only deployment commands — NOT executed; approval required

Run stage by stage in Bash after approval. Do not use aggregate Makefile deployments, migrations,
existing Nova image tags or frontend publishing. Before writes, verify the identity and current
ECR lifecycle headroom; if the additional image could expire ANY existing image, stop without push.
Last known retention is 10, but it must be rechecked rather than assumed. The stored ECR stack's
older retention-template drift is a separate issue; do not redeploy or alter that stack here.

```bash
set -euo pipefail
export AWS_PROFILE=spry-friend AWS_REGION=us-east-1
source infra/scripts/aws-target.sh
aws_target_init
read -r -p 'Secret ARN returned by helper (not the key): ' GEMINI_API_KEY_SECRET_ARN
export GEMINI_API_KEY_SECRET_ARN
RELEASE_TAG="lab6-gemini35-$(date -u +%Y%m%dt%H%M%Sz)-$(python3 -c 'import uuid; print(uuid.uuid4().hex[:8])')"
REPOSITORY=891447916595.dkr.ecr.us-east-1.amazonaws.com/meetings-backend
umask 077
ROLLBACK_DIR=$(mktemp -d /private/tmp/spry-gemini-rollback.XXXXXXXX)
aws_spry lambda get-function --function-name meetings-agenda-parser \
  --query '{image:Code.ResolvedImageUri,architecture:Configuration.Architectures,role:Configuration.Role}' \
  --output json > "$ROLLBACK_DIR/parser-image.json"
aws_spry cloudformation get-template --stack-name meetings-ai --output json > "$ROLLBACK_DIR/template.json"
aws_spry cloudformation describe-stacks --stack-name meetings-ai \
  --query 'Stacks[0].Parameters' --output json > "$ROLLBACK_DIR/parameters.json"
aws_spry ecr get-lifecycle-policy --repository-name meetings-backend
aws_spry ecr describe-images --repository-name meetings-backend \
  --query 'imageDetails[].{digest:imageDigest,pushed:imagePushedAt,tags:imageTags}'
# STOP until review confirms this push cannot expire existing images.
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
# Require architecture arm64 and OS linux; inspect image metadata/source before preview.
AWS_PROFILE=spry-friend AWS_REGION=us-east-1 \
GEMINI_API_KEY_SECRET_ARN="$GEMINI_API_KEY_SECRET_ARN" \
AI_IMAGE_URI="$IMAGE_URI" AI_LAMBDA_ARCH=arm64 AI_EXECUTE=0 \
PARSER_MODEL=gemini-3.5-flash-lite PARSER_BILLING_TIER=free PARSER_CONCURRENCY=0 \
  bash infra/scripts/ai-deploy.sh
aws_spry cloudformation list-change-sets --stack-name meetings-ai
read -r -p 'Exact reviewed change-set ARN: ' APPROVED_CHANGE_SET_ARN
aws_spry cloudformation describe-change-set --change-set-name "$APPROVED_CHANGE_SET_ARN"
# Execute ONLY with deployment approval, after review matches the resource table above:
aws_spry cloudformation execute-change-set --change-set-name "$APPROVED_CHANGE_SET_ARN"
aws_spry cloudformation wait stack-update-complete --stack-name meetings-ai
```

The preview script verifies secret ARN/ownership/current-version metadata without fetching its
value, checks image architecture, copies public Cognito/CORS settings only, and does not execute by
default. Never print SecretString or full secret/API error bodies. Reuse this exact image/preview
rather than building a second artifact for execution. Preserve rollback files privately/durably.

## Postdeployment checks and rollback

Verify deployed digest, arm64, model 3.5, prompt v2, mock=0, exact secret ARN, no plaintext API key or
DB variables, GetSecretValue-only permission, same URL/Cognito/CORS, unchanged log group and budget.
Unauthenticated parser POST must return 401 without secret retrieval/inference. Do not repeat the
local real probe. A separately approved deployed UI parse is still needed to prove the complete
Cognito -> Lambda -> secret -> Gemini -> review -> explicit save -> reopen flow. Record usage and
latency and keep synthetic notes for initial validation. No direct database changes are needed.

If deployment verification fails, stop. A reviewed rollback restores the previous parser image,
matching model/environment and role policy from the backup; do not change backend/frontend or
remove agendas/data/logs/secrets. Keep the new secret and its versions unless cleanup is separately
authorized. Returning to the old Nova image restores prior code but not Nova's zero quotas.

## Validation receipt

Backend: 150 passed, 6 skipped. Frontend: 43 passed. Python lint/changed-file format, frontend
lint/full format and TypeScript/Vite build, CloudFormation lint, shell syntax and whitespace checks
passed. Existing bundle-size warning remains. Only mocked tests were run by this preparation;
the successful real Gemini result above was provided by the user. No AWS/model API calls were made.
