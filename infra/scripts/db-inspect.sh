#!/usr/bin/env bash
# PREPARED ONLY. create/run/remove each require separate user authorization before execution.
# Uses existing VPC, security group, execution role and DB settings, never changes the backend.
set -euo pipefail
cd "$(dirname "$0")/../.."
source infra/scripts/aws-target.sh
mode="${1:-}"
case "$mode" in create|run|remove) ;; *) echo 'Usage: db-inspect.sh create|run|remove (each requires approval)'; exit 1 ;; esac
aws_target_init
name=meetings-db-inspection-lab6
umask 077
tmp=$(mktemp -d)
trap 'rm -rf "$tmp"' EXIT
if [ "$mode" = create ]; then
  image="${INSPECT_IMAGE_URI:?Supply reviewed ARM64 image pinned by digest, containing the inspector}"
  case "$image" in 891447916595.dkr.ecr.us-east-1.amazonaws.com/meetings-backend@sha256:*) ;; *) echo 'Expected target ECR image pinned by digest'; exit 1 ;; esac
  # create-function refuses an existing function; never update or replace it.
  # Fetch config into a mode-600 temporary directory; do not print environment contents.
  aws_spry lambda get-function-configuration --function-name meetings-backend --output json > "$tmp/source.json"
  docker buildx imagetools inspect "$image" --format '{{json .Image}}' | python3 -c 'import json,sys; assert json.load(sys.stdin).get("architecture")=="arm64"'
  python3 - "$tmp/source.json" "$tmp/create.json" "$image" <<'PY'
import json, sys
source = json.load(open(sys.argv[1]))
role = source['Role']
if not role.startswith('arn:aws:iam::891447916595:role/meetings-backend-BackendRole-'):
    raise SystemExit('Unexpected backend execution role')
vpc = source.get('VpcConfig', {})
if vpc.get('VpcId') != 'vpc-095d43a8e0d6631c5' or not vpc.get('SubnetIds') or not vpc.get('SecurityGroupIds'):
    raise SystemExit('Expected existing meetings backend VPC configuration')
if source.get('Architectures') != ['arm64']:
    raise SystemExit('Expected ARM64 backend architecture')
allowed = {'DATABASE_URL','DB_HOST','DB_PORT','DB_USER','DB_PASSWORD','DB_NAME'}
env = {k: v for k, v in source.get('Environment', {}).get('Variables', {}).items() if k in allowed}
if not env.get('DATABASE_URL') and not all(env.get(k) for k in ['DB_HOST','DB_USER','DB_PASSWORD','DB_NAME']):
    raise SystemExit('Backend DB configuration incomplete')
config = {'FunctionName': 'meetings-db-inspection-lab6', 'PackageType': 'Image',
          'Code': {'ImageUri': sys.argv[3]}, 'Architectures': ['arm64'],
          'ImageConfig': {'Command': ['app.diagnostics.db_inspection.handler']},
          'Role': role, 'MemorySize': 128, 'Timeout': 60,
          'VpcConfig': {k: vpc[k] for k in ['SubnetIds', 'SecurityGroupIds']},
          'Environment': {'Variables': env},
          'Tags': {'PROJECT_NAME': 'meetings', 'PURPOSE': 'lab6-readonly-inspection'}}
json.dump(config, open(sys.argv[2], 'w'))
PY
  aws_spry lambda create-function --cli-input-json "file://$tmp/create.json" --query FunctionName --output text
  aws_spry lambda wait function-active-v2 --function-name "$name"
  echo 'Created private inspector; NOT invoked. No URL or invocation permissions were created.'
else
  # Do not invoke/delete an unrelated function with the same name.
  aws_spry lambda list-tags --resource "arn:aws:lambda:us-east-1:$SPRY_ACCOUNT:function:$name" --output json > "$tmp/tags.json"
  python3 - "$tmp/tags.json" <<'PY'
import json,sys
t=json.load(open(sys.argv[1])).get('Tags',{})
if t.get('PROJECT_NAME')!='meetings' or t.get('PURPOSE')!='lab6-readonly-inspection':
    raise SystemExit('Inspector ownership tags do not match; stopped')
PY
  if [ "$mode" = run ]; then
    # Fixed event only; no SQL arguments, HTTP request, migration, seed, or model invocation.
    aws_spry lambda invoke --function-name "$name" --cli-binary-format raw-in-base64-out \
      --payload '{"operation":"inspect_schema"}' --cli-read-timeout 75 \
      --query FunctionError --output text "$tmp/result.json" > "$tmp/function-error"
    [ "$(cat "$tmp/function-error")" = None ] || { echo 'Inspector runtime failed; inspect sanitized diagnostics'; exit 1; }
    cat "$tmp/result.json"
    echo
  else
    aws_spry lambda delete-function --function-name "$name"
    echo 'Removed only the ownership-checked temporary inspector. Existing backend/parser/logs unchanged.'
    echo 'Its separate /aws/lambda/meetings-db-inspection-lab6 log group may remain; see cleanup instructions.'
  fi
fi
