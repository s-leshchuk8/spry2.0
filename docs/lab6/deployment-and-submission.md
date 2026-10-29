> Current status (2026-10-29): Gemini is deployed and authenticated smoke parsing passed.
> This runbook includes historical Nova instructions; do not redeploy them.
> Use [final report](final-report.md), [manual verification](manual-verification.md) and
> [submission checklist](submission-checklist.md) for remaining work.

# Lab 6 deployment and submission checklist

**Local Gemini candidate:** see [gemini-replacement.md](gemini-replacement.md). Gemini 3.5 Flash-Lite
and agenda-v2-gemini are prepared locally. The user reports one successful real structured-output
probe; no Gemini AWS deployment has occurred. See [release plan](gemini-release-plan.md).
Earlier Nova deployment/evaluation entries below are historical. Keep all real-result cells pending.

Authoritative next-phase commands: [release runbook](release-runbook.md).
Database access: [private read-only inspection](database-inspection.md).
Migration choices: [evidence-driven scenarios](../lab6-migrations.md).
No commands in this document were executed against AWS during local preparation.

## Gates before release

- [ ] Profile `spry-friend`, account `891447916595`, region `us-east-1` explicitly verified by the guard.
- [ ] No credential overrides; `.env` credential-free. Do not use default credentials or eu-central-1 legacy spry resources.
- [ ] Database inspection approved, actual revision/schema/constraints collected and reviewed.
- [ ] Migration strategy selected from evidence and rehearsed on disposable PostgreSQL; historical source not rewritten blindly.
- [ ] Current API/parser images and frontend assets backed up/protected from expiry/deletion.
- [ ] Same explicit release tag/digest used throughout; parser image architecture verified.
- [ ] Backend/parser change sets reviewed for replacements/deletions, IAM, environment and URLs.
- [ ] Existing log events preserved: no log-group creation/deletion/import or retention shortening.
- [ ] Existing `meetings-monthly-5usd` budget reused; correct email/thresholds remain.
- [ ] Reserved concurrency omitted (`PARSER_CONCURRENCY=0`), not set to zero on the Lambda.
- [ ] Real Nova selected, `PARSER_MOCK=0`, no parser DB settings or Mantle permissions.
- [ ] Instructor approval obtained for Nova instead of the originally required Claude.

The user reports Opus 5.5 and Haiku 5.5 AccessDenied in the target account. Nova Micro via boto3
Converse is the selected fallback; this does not satisfy the literal Claude requirement without
instructor approval. Previous read-only audit metadata availability is not proof of real inference.

## Verification and evidence (after explicit deployment/inference approval)

- [ ] Unsigned/invalid-token parser request → 401; non-POST → 405; oversized input → 413 before inference.
- [ ] CORS allows the actual frontend and local origins, POST and authorization/content-type.
- [x] Real smoke model is `gemini-3.5-flash-lite`, prompt `agenda-v2-gemini`, not `mock`; see authenticated receipt.
- [ ] Progress/Cancel work; canceled late responses do not overwrite form values.
- [ ] Suggested fields are editable and marked until edited; missing facts remain empty.
- [ ] Save is explicit through the normal API; reopened final agenda and original suggestion persist.
- [ ] Another user cannot read/save the meeting's agenda.
- [ ] Manual agendas and ordinary meeting CRUD work independently of Bedrock.
- [ ] Five real outputs collected in [evaluation table](evaluation.md); actual correctness/invention counts recorded.
- [ ] One real log line collected; no mocked measurements presented as real.
- [ ] Observed-outcome sections completed in [Step 5 answers](step5-answers.md).

## Read actual CloudWatch evidence

After a separately approved real parse:

```bash
aws logs filter-log-events --profile spry-friend --region us-east-1 \
  --log-group-name /aws/lambda/meetings-agenda-parser \
  --filter-pattern '"agenda_parsed"' --query 'events[].message' --output text
```

Select the matching successful event with user/model/prompt_version/input_tokens/output_tokens/
latency_ms/cost_usd/outcome. Do not include tokens, raw pasted text or credentials. Logs for local
mock calls explicitly show model `mock` and zero usage/cost and cannot be submitted as real inference.

## Recording: at most 45 seconds

Prepare a signed-in deployed browser and an existing test meeting. Keep secrets and DevTools off screen.

- 0–8 s: meeting details → Add / view agenda; paste the Ukrainian example.
- 8–23 s: Parse; show progress and suggested fields.
- 23–34 s: correct one field; show its suggested badge disappear.
- 34–43 s: explicitly Save and reopen to demonstrate persistence.

Do not edit a failed/model-mock invocation into a fake success. Retain the matching actual log.

## Submission still outstanding

- [ ] Approved commit/push and commit link (not authorized in this local phase).
- [ ] Deployed GIF/MP4 ≤45 seconds.
- [ ] Five-row real evaluation table, raw JSON outputs and measured usage/cost/latency.
- [ ] One actual CloudWatch JSON event.
- [ ] Final empirical answers, ADR, C4 diagram and instructor approval for the model deviation.

No new permanent inspection infrastructure is required. Clean up only the ownership-checked
temporary inspector after saving metadata; never delete shared parser/backend log groups or data.
