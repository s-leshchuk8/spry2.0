# Real parser failure: zero Nova Micro account quotas

Read-only evidence verified with profile spry-friend, account 891447916595, us-east-1.
Model remains us.amazon.nova-micro-v1:0; mock is disabled.

## Confirmed root cause

The applied account quotas returned by both ListServiceQuotas and GetServiceQuota are:

| Quota | Code | Applied | Adjustable via Service Quotas |
|---|---|---:|---|
| Nova Micro cross-region tokens/minute | L-DC7FF66C | 0 | Yes |
| Nova Micro cross-region requests/minute | L-3F110E0F | 0 | No |
| Nova Micro model tokens/day | L-D2912E70 | 0 | No |

Direct on-demand Nova Micro RPM/TPM are also zero; changing to the foundation model ID would not
solve this and is not proposed. Published AWS default quotas are not this account's applied limits.
The account-level reason AWS assigned zero quotas is not established; do not guess billing status.

Three actual handler records show outcome busy, 0 returned input/output tokens, latency 968/116/130 ms.
CloudWatch AWS/Bedrock InvocationThrottles for this profile has sum 3; AWS/Lambda Throttles sum 0.
The handler classifies provider HTTP 429 / throttling as HTTP 429, body error busy. Frontend maps
429 to the observed busy message; it does not map 403/502/503 or malformed output to that message.
Existing logs omit provider code/message, so no exact provider message is claimed or printed.
No fresh authenticated parse was attempted to capture a new HTTP response because inference needs
approval. The recorded outcome, deployed mapping, metric correlation and zero applied quotas
establish a provider quota blocker rather than a frontend masking or Lambda-concurrency failure.

Lambda Active/Successful, timeout 30 seconds, no reserved concurrency, account concurrency 10.
Inference profile ACTIVE with US destinations east-1/east-2/west-2; model availability and entitlement
AVAILABLE, authorization AUTHORIZED. Reviewed deployed IAM allows this exact profile and Nova Micro
foundation models through it. No widening of IAM or new resource is required. This failure occurs
before output validation; it does not prove real model-quality/schema behavior until inference works.

## Smallest fix — external quota enablement, NOT redeployment

Keep application/model/prompt/tool contracts unchanged. Enable positive cross-region RPM, TPM and
the daily token allowance for Nova Micro in this account and region. Waiting/retry loops, reducing
maxTokens, increasing Lambda concurrency or changing IAM cannot make a zero quota usable.
No parser/frontend production code change is needed for this root cause. Manual meeting and agenda
entry remain usable. Token increase alone is insufficient while request/day limits remain zero.

No existing TPM increase request was found. Prepared request, not submitted:

- Account 891447916595, us-east-1, Bedrock Runtime Converse, us.amazon.nova-micro-v1:0.
- University Lab 6: one student, five evaluation cases, tiny peak load; no batch or production traffic.
- Request cross-region TPM 20,000; ask AWS to enable corresponding RPM and daily allowances
  (suggested small lab targets 5 RPM and 100,000 tokens/day, or AWS-supported minimum positive values).
- Existing request/TPM/day quotas all zero; model authorized/profile ACTIVE; 3 Bedrock throttles,
  no Lambda throttles. Current inferenceConfig maxTokens=4096; max 10,000 input characters;
  at most two Converse calls per user parse, second only for invalid schema. No automatic throttle
  retry. Plan to run one short agenda at a time, not burst traffic. Most lab prompts are well below
  the input limit; no measured output-token estimate is claimed because no generation succeeded.
- Please identify any account eligibility restriction if quota enablement is unavailable.

Owner approval is required before submitting. Proposed adjustable-TPM command (NOT executed):

```bash
source infra/scripts/aws-target.sh
AWS_PROFILE=spry-friend AWS_REGION=us-east-1 aws_target_init
aws_spry service-quotas request-service-quota-increase \
  --service-code bedrock --quota-code L-DC7FF66C --desired-value 20000
```

Use its request/case ID for the additional zero-RPM/daily support discussion, avoiding duplicate
requests. Do not send RequestServiceQuotaIncrease for non-adjustable codes or purchase provisioned
throughput as a workaround. Support/approval availability is determined by AWS; do not upgrade a
support plan, change billing, create cases or alter any quota without authorization.
Console route: Service Quotas -> Amazon Bedrock -> us-east-1 -> Cross-region model inference tokens
per minute for Amazon Nova Micro -> Request increase. Include the prepared explanation when AWS
support follows up; use Support's service-limit route for non-adjustable limits as available.

## Regression validation

Added a full parser-through-Lambda mocked Converse throttling regression: one call, no retry,
HTTP 429/busy, zero returned usage and no provider detail leakage. Added frontend coverage proving
429 does not automatically retry and manual agenda persistence remains possible. Existing tests
validate tool schema/response contracts, validation retry and reviewed agenda -> meeting creation
with unchanged original suggestion. No runtime code was changed.

## Gate before another real test

1. Obtain approval to submit quota enablement. No production changes were made by this investigation.
2. Wait for AWS processing; re-read all three applied quotas and require positive sufficient values.
3. Obtain separate approval for one bounded real parser test. No redeploy is required if only quotas
   change. Confirm HTTP 200, record_agenda input passes Pydantic, nonzero usage and editable output.
4. Explicitly create/save and reopen only a test meeting under the signed-in owner's control; collect
   actual evaluation evidence. Stop on any new provider error rather than blindly retrying.

The parser is locally code-ready but **NOT ready for another real attempt while quotas remain zero**.
Raw CloudWatch evidence is retained privately under /private/tmp; sanitized quota evidence is in
nova-quota-evidence.json. No model invocation, quota/support request, deployment, database change,
IAM change, commit or push occurred in this investigation.

Primary references:
- https://docs.aws.amazon.com/bedrock/latest/userguide/quotas-runtime.html
- https://repost.aws/knowledge-center/bedrock-throttling-error
- https://docs.aws.amazon.com/servicequotas/latest/userguide/request-quota-increase.html
