#!/usr/bin/env bash
# Deploys infra/reports.yaml. VPC, subnets, security group and DB settings are
# read from the already-deployed API Lambda, so nothing has to be typed in by hand.
set -euo pipefail
cd "$(dirname "$0")/../.."

PROJECT="${PROJECT:-meetings}"
BACKEND_FUNCTION="${BACKEND_FUNCTION:-$PROJECT-backend}"
STACK="$PROJECT-reports"
BUILDER="$PROJECT-report-builder"
REGION="${AWS_REGION:-us-east-1}"
EMAIL="${REPORT_EMAIL:-}"
DOMAIN="${REPORT_DOMAIN:-}"
SCHEDULE="${REPORT_SCHEDULE:-cron(0 7 ? * MON *)}"
ARCH="${REPORT_LAMBDA_ARCH:-x86_64}"
IMAGE="${BUILDER_IMAGE_URI:-}"

[ -n "$EMAIL" ] || { echo "Set REPORT_EMAIL=your@email in .env"; exit 1; }

if ! out=$(aws lambda get-function-configuration --function-name "$BACKEND_FUNCTION" \
    --query '[VpcConfig.VpcId, join(`,`, VpcConfig.SubnetIds), join(`,`, VpcConfig.SecurityGroupIds)]' \
    --output text 2>&1); then
  echo "Cannot read Lambda '$BACKEND_FUNCTION': $out"
  echo "Deploy the API first (make aws-backend-deploy) or set BACKEND_FUNCTION=<name>."
  exit 1
fi
IFS=$'\t' read -r VPC_ID SUBNETS SGS <<<"$out"
if [ -z "$VPC_ID" ] || [ "$VPC_ID" = None ]; then
  echo "Lambda '$BACKEND_FUNCTION' is not attached to a VPC - unexpected for this lab."; exit 1
fi

if [ -z "$IMAGE" ]; then   # no new build: reuse the image the builder already runs
  IMAGE=$(aws lambda get-function --function-name "$BUILDER" --query 'Code.ImageUri' --output text)
fi

RTBS=$(aws ec2 describe-route-tables --filters "Name=association.subnet-id,Values=$SUBNETS" \
  --query 'join(`,`, RouteTables[].RouteTableId)' --output text)
if [ -z "$RTBS" ] || [ "$RTBS" = None ]; then   # subnets use the VPC's main route table
  RTBS=$(aws ec2 describe-route-tables \
    --filters "Name=vpc-id,Values=$VPC_ID" "Name=association.main,Values=true" \
    --query 'join(`,`, RouteTables[].RouteTableId)' --output text)
fi

owns() {  # does our stack already own this logical resource?
  [ "$(aws cloudformation describe-stack-resources --stack-name "$STACK" \
      --query "length(StackResources[?LogicalResourceId=='$1'])" --output text 2>/dev/null || echo 0)" != 0 ]
}

if owns S3GatewayEndpoint; then CREATE_EP=true
else
  n=$(aws ec2 describe-vpc-endpoints --filters "Name=vpc-id,Values=$VPC_ID" \
        "Name=service-name,Values=com.amazonaws.$REGION.s3" --query 'length(VpcEndpoints)' --output text)
  if [ "$n" = 0 ]; then CREATE_EP=true; else CREATE_EP=false; fi
fi

if owns RecipientIdentity; then CREATE_ID=true
elif aws sesv2 get-email-identity --email-identity "$EMAIL" >/dev/null 2>&1; then CREATE_ID=false
else CREATE_ID=true; fi

status=$(aws cloudformation describe-stacks --stack-name "$STACK" \
  --query 'Stacks[0].StackStatus' --output text 2>/dev/null || true)
if [ "$status" = ROLLBACK_COMPLETE ]; then
  echo "Stack $STACK is in ROLLBACK_COMPLETE after a failed create; recovery needs review"
  echo "Inspect the failed stack and approve cleanup separately. No deletion performed."; exit 1
fi

echo "VPC=$VPC_ID subnets=$SUBNETS sg=$SGS routetables=$RTBS"
echo "image=$IMAGE arch=$ARCH s3-endpoint-in-stack=$CREATE_EP ses-identity-in-stack=$CREATE_ID"

show_failures() {
  echo; echo "Deploy failed. Reasons from CloudFormation:"
  aws cloudformation describe-stack-events --stack-name "$STACK" \
    --query "StackEvents[?contains(ResourceStatus,'FAILED')].[LogicalResourceId,ResourceStatusReason]" \
    --output table 2>/dev/null || true
}

aws cloudformation deploy --stack-name "$STACK" --template-file infra/reports.yaml \
  --capabilities CAPABILITY_IAM --no-fail-on-empty-changeset --tags PROJECT_NAME="$PROJECT" \
  --parameter-overrides \
    ProjectName="$PROJECT" VpcId="$VPC_ID" "PrivateSubnetIds=$SUBNETS" \
    "PrivateRouteTableIds=$RTBS" "LambdaSecurityGroupIds=$SGS" BuilderImageUri="$IMAGE" \
    Architecture="$ARCH" CreateS3Endpoint="$CREATE_EP" CreateRecipientIdentity="$CREATE_ID" \
    RecipientEmail="$EMAIL" "DomainName=$DOMAIN" "ScheduleExpression=$SCHEDULE" || { show_failures; exit 1; }

"$(dirname "$0")/report-env.sh" sync

echo
aws cloudformation describe-stacks --stack-name "$STACK" \
  --query "Stacks[0].Outputs[].[OutputKey, OutputValue]" --output table
echo "Next: confirm the SES verification email sent to $EMAIL$( [ -n "$DOMAIN" ] && echo ' and add the DKIM CNAME records above to DNS')."