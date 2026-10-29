#!/usr/bin/env bash
# Explicit invocation only. Default previews a change set; never deletes a stack.
set -euo pipefail
cd "$(dirname "$0")/../.."
source infra/scripts/aws-target.sh
aws_target_init
PROJECT="${PROJECT:-meetings}"
[ "$PROJECT" = meetings ] || { echo 'Expected project meetings'; exit 1; }
STACK=meetings-ai
BACKEND_FUNCTION=meetings-backend
ARCH="${AI_LAMBDA_ARCH:-arm64}"
IMAGE="${AI_IMAGE_URI:?Supply a reviewed image URI; reusing the old parser image is unsafe}"
SECRET="${GEMINI_API_KEY_SECRET_ARN:?Supply the existing Gemini secret ARN, never its value}"
[[ "$SECRET" =~ ^arn:aws:secretsmanager:us-east-1:891447916595:secret:meetings/gemini-api-key-[A-Za-z0-9]{6}$ ]] || { echo "Unexpected secret ARN"; exit 1; }
BUDGET="${EXISTING_BUDGET_NAME:-meetings-monthly-5usd}"
[ "$BUDGET" = meetings-monthly-5usd ] || { echo 'Expected the existing project budget'; exit 1; }
case "$IMAGE" in
  891447916595.dkr.ecr.us-east-1.amazonaws.com/meetings-backend:*) ;;
  891447916595.dkr.ecr.us-east-1.amazonaws.com/meetings-backend@sha256:*) ;;
  *) echo 'Image must be in the verified account/region/repository'; exit 1 ;;
esac
# Metadata only: never fetch the secret value in a deployment script.
aws_spry secretsmanager describe-secret --secret-id "$SECRET" \
  --query '{arn:ARN,tags:Tags,deleted:DeletedDate,versions:VersionIdsToStages}' --output json | \
  python3 -c 'import json,sys; d=json.load(sys.stdin); assert d["arn"]==sys.argv[1] and not d.get("deleted"); assert {t["Key"]:t["Value"] for t in d.get("tags",[])}.get("PROJECT_NAME")=="meetings"; assert any("AWSCURRENT" in v for v in d.get("versions",{}).values())' "$SECRET"
# Pin mutable release tags to a digest before inspecting or previewing the image.
if [[ "$IMAGE" != *@sha256:* ]]; then
  tag="${IMAGE##*:}"
  digest=$(aws_spry ecr describe-images --repository-name meetings-backend --image-ids "imageTag=$tag" --query 'imageDetails[0].imageDigest' --output text)
  [[ "$digest" = sha256:* ]] || { echo 'Image tag did not resolve to a digest'; exit 1; }
  IMAGE="891447916595.dkr.ecr.us-east-1.amazonaws.com/meetings-backend@$digest"
fi
concurrency="${PARSER_CONCURRENCY:-0}"
[[ "$concurrency" =~ ^[0-5]$ ]] || { echo 'PARSER_CONCURRENCY must be 0..5'; exit 1; }
if [ "$concurrency" -gt 0 ]; then
  available=$(aws_spry lambda get-account-settings --query AccountLimit.UnreservedConcurrentExecutions --output text)
  [ "$available" -ge "$((100 + concurrency))" ] || { echo 'Insufficient quota for reserved concurrency; use 0 to omit it'; exit 1; }
fi
case "$ARCH" in arm64) expected=arm64 ;; x86_64) expected=amd64 ;; *) exit 1 ;; esac
# Requires prior ECR Docker login. Reads the actual registry config, not a caller-supplied label.
actual=$(docker buildx imagetools inspect "$IMAGE" --format '{{json .Image}}' | python3 -c 'import json,sys; d=json.load(sys.stdin); print(d.get("architecture", "multi-platform-unsupported"))')
[ "$actual" = "$expected" ] || { echo 'Image architecture mismatch; no deployment performed'; exit 1; }
status=$(aws_spry cloudformation describe-stacks --stack-name "$STACK" --query 'Stacks[0].StackStatus' --output text)
[ "$status" != ROLLBACK_COMPLETE ] || { echo 'Failed-stack recovery requires separate review; nothing deleted'; exit 1; }
# Reuse existing resources. Read-only checks precede change-set creation.
aws_spry logs describe-log-groups --log-group-name-prefix /aws/lambda/meetings-agenda-parser --query 'logGroups[].logGroupName' --output json | python3 -c 'import json,sys; assert "/aws/lambda/meetings-agenda-parser" in json.load(sys.stdin)'
aws_spry budgets describe-budget --account-id "$SPRY_ACCOUNT" --budget-name "$BUDGET" --query 'Budget.{amount:BudgetLimit.Amount,unit:BudgetLimit.Unit,period:TimeUnit}' --output json | python3 -c 'import json,sys; d=json.load(sys.stdin); assert float(d["amount"])==5 and d["unit"]=="USD" and d["period"]=="MONTHLY"'
umask 077
tmp=$(mktemp)
trap 'rm -f "$tmp" "$tmp.src"' EXIT
# Public settings only: no DB settings, passwords, or other API environment values are fetched.
aws_spry lambda get-function-configuration --function-name "$BACKEND_FUNCTION" \
  --query 'Environment.Variables.{cors:CORS_ORIGINS,region:COGNITO_REGION,pool:COGNITO_USER_POOL_ID,client:COGNITO_CLIENT_ID}' \
  --output json > "$tmp.src"
python3 - "$tmp.src" "$tmp" "$IMAGE" "$ARCH" "$BUDGET" <<'PY'
import json, os, sys
src = json.load(open(sys.argv[1]))
if not all(src.values()):
    raise SystemExit("API must have CORS and Cognito configured")
params = {"ProjectName": "meetings", "ImageUri": sys.argv[3], "Architecture": sys.argv[4],
          "CorsOrigins": src["cors"], "CognitoRegion": src["region"],
          "CognitoUserPoolId": src["pool"], "CognitoClientId": src["client"],
          "ParserModel": os.environ.get("PARSER_MODEL") or "gemini-3.5-flash-lite",
          "PromptVersion": "agenda-v2-gemini",
          "GeminiApiKeySecretArn": os.environ["GEMINI_API_KEY_SECRET_ARN"],
          "BillingTier": os.environ.get("PARSER_BILLING_TIER") or "free",
          "ParserConcurrency": os.environ.get("PARSER_CONCURRENCY") or "0",
          "ExistingBudgetName": sys.argv[5]}
json.dump([{"ParameterKey": k, "ParameterValue": v} for k, v in params.items()], open(sys.argv[2], "w"))
PY
# Even with --no-execute-changeset this CREATES an AWS change set: approval is required to run.
preview=(--no-execute-changeset)
if [ "${AI_EXECUTE:-0}" = 1 ]; then preview=(); fi
aws_spry cloudformation deploy --stack-name "$STACK" --template-file infra/ai.yml \
  --capabilities CAPABILITY_IAM --no-fail-on-empty-changeset --tags PROJECT_NAME=meetings \
  --parameter-overrides "file://$tmp" "${preview[@]}"
