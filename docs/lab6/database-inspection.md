# Private Aurora inspection — prepared, NOT created or invoked

Target: spry-friend, 891447916595, us-east-1, database `meetings`.

## Why a temporary Lambda

The audit found private Aurora with Data API disabled, PostgreSQL ingress limited to the backend
security group, and no running EC2 access host. If the owner already has a VPC-connected read-only
client, run the fixed SELECTs from `backend/app/diagnostics/db_inspection.py` there instead. Do not
open public ingress or enable Data API merely for inspection.

Otherwise create one temporary, private Lambda using the reviewed backend image and existing
backend VPC/subnets/security group/execution role. This reuses the established database path
without updating/restarting the production API, adding IAM policies, creating a bastion, NAT, VPC,
or permanent database service. The inspector is not routed through FastAPI or a Function URL.
The existing backend handler is unchanged; no diagnostic action is added to its public surface.

## Safety properties

- Exact event only: `{"operation":"inspect_schema"}`. No SQL, database name or table name arguments.
- Handler checks account, region and exact temporary function name before connecting.
- Fixed SELECTs read transaction status, public table/column/constraint metadata and `version_num` only.
  No meetings/agendas row contents are fetched. No Alembic/seed/ORM imports, upgrade/downgrade/stamp.
- PostgreSQL startup option `default_transaction_read_only=on`; confirm transaction_read_only is `on`
  before reading metadata; statement timeout 5 s, lock timeout 1 s, TLS required, connect timeout 20 s.
- Always roll back and close; never commit. No DDL/DML, advisory locks or user-defined SQL.
- Missing version table yields `null`; an empty table yields `[]`. Neither means “safe to initialize.”
- Failures return an allowlisted stage/category, exception class, SQLSTATE (when available), and elapsed milliseconds. Raw messages are never returned or logged. Stages distinguish configuration, network/connect, authentication, transaction setup and metadata query; message matching is used internally only to classify connection failures.
- Settings are copied only from existing backend DB keys, via private mode-600 files in a mode-700
  temporary directory. They are never printed or put in command-line arguments or repository files.
- Temporary Lambda has no URL, public permission, event source or schedule; IAM-authorized invocation only.
- 128 MB, timeout 60 s; no reserved concurrency. One invocation may wake Aurora and incurs normal Lambda/
  database charges, even though it uses only read-only SQL. Creation and invocation each need approval.

The existing backend role already has VPC/log permissions and database security-group access. The
script verifies its target-account role prefix and VPC, and copies no Cognito/parser settings.
It is still an existing application DB login, not a newly provisioned read-only DB user: fixed SQL,
read-only transaction and no user SQL are the controls. Do not claim a new least-privilege DB role.

## Prepared procedure (separate approvals required)

1. Review the inspector code and tests. Build the backend ARM64 image as described in
   `release-runbook.md`. Pushing it does not update the backend, run migrations or invoke anything.
2. Resolve the new image digest and confirm it contains the inspector; do not use the currently
   deployed October image, which predates this code. Export `INSPECT_IMAGE_URI` pinned by digest.
3. Approve creation, then run:

```bash
AWS_PROFILE=spry-friend AWS_REGION=us-east-1 \
INSPECT_IMAGE_URI="$IMAGE_URI" bash infra/scripts/db-inspect.sh create
```

This creates only `meetings-db-inspection-lab6`, reusing existing role/network. It refuses to update
an existing function with that name. No function is invoked by `create`.

4. Approve a single inspection, then run:

```bash
AWS_PROFILE=spry-friend AWS_REGION=us-east-1 bash infra/scripts/db-inspect.sh run
```

The result contains revision rows, table types, columns/defaults/nullability and constraint/FK
SQL definitions, not user data. Save the result privately and choose a scenario in
`../lab6-migrations.md`. An error is not evidence that a migration was never applied. Cold Aurora
may require a later approved retry; do not repeatedly invoke or broaden network access automatically.

5. Approve cleanup, then run:

```bash
AWS_PROFILE=spry-friend AWS_REGION=us-east-1 bash infra/scripts/db-inspect.sh remove
```

This checks ownership tags and deletes only the temporary function, never the backend/parser.
Lambda manages its temporary ENIs; do not manually delete shared VPC/security-group resources.
No role, secret, subnet or database was created, so none needs deleting.

The separate automatically-created inspector log group may remain. After saving evidence, and
ONLY if it was created by this inspection, obtain approval to remove it:

```bash
aws logs delete-log-group --profile spry-friend --region us-east-1 \
  --log-group-name /aws/lambda/meetings-db-inspection-lab6
```

Never substitute `/aws/lambda/meetings-agenda-parser` or `/aws/lambda/meetings-backend`. Existing
parser logs must remain intact. The inspector script only removes its private local temporary files
automatically; it never automatically deletes any cloud resources after an error.


## Bounded diagnostic follow-up

The diagnostic handler still uses direct psycopg keyword arguments from `settings.sqlalchemy_url`;
it does not import the application engine or perform SQLAlchemy initialization, migrations or seeds.
It preserves TLS, a 20-second connect timeout and startup-enforced read-only transactions. A failed
connection may have no SQLSTATE (libpq connection errors often do not supply one); the category is
then a bounded classifier, not proof of a particular network or credential root cause.

A unique run may also package this exact handler/config module and reviewed Linux ARM64 binary
wheels in a Python 3.12 ZIP, avoiding an ECR image push. Change only the temporary copy's exact
function-name guard. Verify code hash, architecture, database endpoint, existing role and networking
before invoking. Create/tag a unique log group explicitly, record a unique run ownership tag on both
resources, and verify both ownership tags before cleanup. Never reuse a prior run's resource names.
The authorized workflow is one invocation only, with CLI retries disabled; a failed diagnostic does
not authorize a retry or another Lambda. Preserve sanitized evidence locally after deleting the
owned function and log group. No existing IAM, networking or application resources are changed.
