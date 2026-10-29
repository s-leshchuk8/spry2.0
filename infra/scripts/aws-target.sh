#!/usr/bin/env bash
# Source and call aws_target_init before any operation. Executing this file only verifies STS.
aws_target_init() {
  if [ "${AWS_PROFILE+x}" = x ] && [ -z "$AWS_PROFILE" ]; then
    echo 'An explicitly empty AWS_PROFILE is not permitted.' >&2; return 1
  fi
  SPRY_PROFILE="${AWS_PROFILE:-spry-friend}"
  SPRY_REGION="${AWS_REGION:-us-east-1}"
  SPRY_ACCOUNT=891447916595
  if [ "$SPRY_PROFILE" != spry-friend ] || [ "$SPRY_REGION" != us-east-1 ]; then
    echo 'Only profile spry-friend in us-east-1 is permitted.' >&2; return 1
  fi
  for key in AWS_ACCESS_KEY_ID AWS_SECRET_ACCESS_KEY AWS_SESSION_TOKEN AWS_SECURITY_TOKEN AWS_WEB_IDENTITY_TOKEN_FILE AWS_ROLE_ARN AWS_CONTAINER_CREDENTIALS_FULL_URI AWS_CONTAINER_CREDENTIALS_RELATIVE_URI; do
    if [ -n "${!key:-}" ]; then
      echo "Credential override $key is set; unset it before proceeding (value not printed)." >&2; return 1
    fi
  done
  local actual
  actual=$(aws_spry sts get-caller-identity --query Account --output text) || return 1
  if [ "$actual" != "$SPRY_ACCOUNT" ]; then
    echo 'Account mismatch; no further AWS operations performed.' >&2; return 1
  fi
  export AWS_PROFILE="$SPRY_PROFILE" AWS_REGION="$SPRY_REGION" AWS_DEFAULT_REGION="$SPRY_REGION"
}
aws_spry() {
  command aws --profile "$SPRY_PROFILE" --region "$SPRY_REGION" --no-cli-pager "$@"
}
if [ "${BASH_SOURCE[0]}" = "$0" ]; then
  set -euo pipefail
  aws_target_init
  echo 'Verified target account 891447916595 using spry-friend / us-east-1.'
fi
