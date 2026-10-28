#!/usr/bin/env bash
# Deploys infra/ai.yml. The Cognito settings and CORS origins are read from the API Lambda.
# Run with:  bash infra/scripts/ai-deploy.sh   (normally via `make ai-deploy`)
set -euo pipefail
cd "$(dirname "$0")/../.."

PROJECT="${PROJECT:-meetings}"
BACKEND_FUNCTION="${BACKEND_FUNCTION:-$PROJECT-backend}"
STACK="$PROJECT-ai"
FUNCTION="$PROJECT-agenda-parser"
ARCH="${AI_LAMBDA_ARCH:-x86_64}"
IMAGE="${AI_IMAGE_URI:-}"

if ! CORS=$(aws lambda get-function-configuration --function-name "$BACKEND_FUNCTION" \
    --query 'Environment.Variables.CORS_ORIGINS' --output text 2>&1); then
  echo "Cannot read Lambda '$BACKEND_FUNCTION': $CORS"
  echo "Deploy the API first (make aws-backend-deploy) or set BACKEND_FUNCTION=<name>."; exit 1
fi
if [ -z "$CORS" ] || [ "$CORS" = None ]; then
  echo "The API Lambda has no CORS_ORIGINS variable."; exit 1
fi

if [ -z "$IMAGE" ]; then   # no new build: reuse the image the parser already runs
  IMAGE=$(aws lambda get-function --function-name "$FUNCTION" --query 'Code.ImageUri' --output text 2>/dev/null) || {
    echo "No image given and $FUNCTION does not exist yet: use make ai-deploy"; exit 1; }
fi

status=$(aws cloudformation describe-stacks --stack-name "$STACK" \
  --query 'Stacks[0].StackStatus' --output text 2>/dev/null || true)
if [ "$status" = ROLLBACK_COMPLETE ]; then
  echo "Stack $STACK is in ROLLBACK_COMPLETE after a failed create; deleting it first"
  aws cloudformation delete-stack --stack-name "$STACK"
  aws cloudformation wait stack-delete-complete --stack-name "$STACK"
fi

echo "image=$IMAGE arch=$ARCH"
echo "cors=$CORS"

show_failures() {
  echo; echo "Deploy failed. Reasons from CloudFormation:"
  aws cloudformation describe-stack-events --stack-name "$STACK" \
    --query "StackEvents[?contains(ResourceStatus,'FAILED')].[LogicalResourceId,ResourceStatusReason]" \
    --output table 2>/dev/null || true
}

aws cloudformation deploy --stack-name "$STACK" --template-file infra/ai.yml \
  --capabilities CAPABILITY_IAM --no-fail-on-empty-changeset --tags PROJECT_NAME="$PROJECT" \
  --parameter-overrides ProjectName="$PROJECT" ImageUri="$IMAGE" Architecture="$ARCH" \
    "CorsOrigins=$CORS" || { show_failures; exit 1; }

# Environment: the API's settings (Cognito...) + PARSER_*. The parser never connects to the
# database, so anything that looks like a password is replaced by a dummy value.
tmp="$(mktemp)"
trap 'rm -f "$tmp" "$tmp.src"' EXIT
aws lambda get-function-configuration --function-name "$BACKEND_FUNCTION" \
  --query 'Environment.Variables' --output json > "$tmp.src"
python3 - "$tmp.src" > "$tmp" <<'PY'
import json, os, sys
src = json.load(open(sys.argv[1])) or {}
env = {k: ("unused" if any(w in k.upper() for w in ("PASSWORD", "SECRET")) else v) for k, v in src.items()}
for k in ("PARSER_PROVIDER", "PARSER_MODEL", "PARSER_EFFORT", "PARSER_MOCK"):
    if os.environ.get(k):
        env[k] = os.environ[k]
print(json.dumps({"Variables": env}))
PY
aws lambda update-function-configuration --function-name "$FUNCTION" \
  --environment "file://$tmp" --query LastUpdateStatus --output text >/dev/null
aws lambda wait function-updated --function-name "$FUNCTION"
echo "agenda-parser environment: set (PARSER_MOCK='${PARSER_MOCK:-}' PARSER_PROVIDER='${PARSER_PROVIDER:-}' PARSER_MODEL='${PARSER_MODEL:-}')"

echo
aws cloudformation describe-stacks --stack-name "$STACK" \
  --query "Stacks[0].Outputs[].[OutputKey, OutputValue]" --output table
