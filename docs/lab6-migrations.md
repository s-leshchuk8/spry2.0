# Deployment gate: verify historical agenda migration

**Do not deploy migrations yet. No existing/shared database was migrated during implementation.**

Repository chain:

`0001 → 0002 → 0003 → 5d5e3ded4830 → 0004_reviewed_agendas`

The historical `5d5e3ded4830` references an unimported `postgresql` and an `agendas` table that no
predecessor creates. Its deployed/applied/stamped history is unknown. Its file is deliberately
unchanged. A fresh `alembic upgrade head` therefore remains blocked by that historical revision.
An additional forward migration cannot bypass a broken predecessor automatically.

## Verification before choosing a path

With separately approved read-only database access, collect a [read-only inspection snapshot](lab6/database-inspection.md) containing the actual
`alembic_version` row(s), deployed migration file versions/checksums, and the `agendas` table's
columns/types, primary/foreign keys, nullability, existing rows and provenance shape. Check every
environment, including developer databases and restored snapshots. Do not print connection secrets.
Take an approved backup before any data/schema change. Rehearse on a disposable copy first.

- **Verified never applied or stamped anywhere:** review `migration-repairs/unapplied-only.patch`.
  It repairs the missing import and creates the missing agenda table before adding the suggestion
  column. Only after verifying that condition may an authorized phase apply this patch and run a
  complete fresh upgrade rehearsal. The patch is prepared, not applied to migration history.
- **Already stamped at `5d5e3ded4830`, no agenda table:** the new forward revision creates the
  one-row-per-meeting table without rewriting the historical migration.
- **Already applied/stamped and compatible agenda table:** the new revision validates the key and
  required columns, then adds `ai_suggestion` if missing. Verify types and cascade foreign key too.
- **Existing incompatible schema/data:** the forward revision stops rather than overwriting it.
  Prepare a specific data-preserving transform after inspection. Do not stamp past failures or
  drop tables to make deployment appear successful.
- **Database at `0003` or earlier while other environments already applied the old revision:**
  do not rewrite history globally. Prepare a separately reviewed bootstrap/data migration that
  reproduces the expected predecessor schema, verify its postconditions, and explicitly approve
  any version reconciliation. No automatic stamping script is supplied.

The new revision's downgrade deliberately refuses to delete reviewed agendas. Rollback is an
application rollback or an explicitly reviewed data recovery operation, not an automatic table drop.

Local API tests build ORM tables only in an isolated test database and do not prove the historical
Alembic chain is deployable. The forward-migration tests exercise only its own upgrade function on
an isolated schema. A full fresh-chain rehearsal remains a deployment prerequisite.

## Evidence-driven decision table

No plan is selected until the inspector result and the history of all relevant environments are reviewed.

| Observed state | Safe next plan (separately approved) |
|---|---|
| No `alembic_version` table, empty table, multiple/unknown revisions | Stop. Identify DB provenance, branches and actual schema. Do not infer a fresh DB or stamp it. |
| `0001` or `0002` | Inventory existing data and forward migration prerequisites; rehearse upgrades on a disposable copy. Historical agenda repair still requires cross-environment evidence. |
| `0003`, no agendas | If the historical revision is proven never applied/stamped anywhere, review the unapplied-only patch and rehearse the full chain. Otherwise use a separately reviewed compatibility/bootstrap strategy, not a blind stamp. |
| `0003`, agendas already exist | Compare columns/types/PK/FKs/data provenance. Repair/adopt the schema with a data-preserving migration based on evidence; do not assume the table is disposable. |
| `5d5e3ded4830`, no agendas | A stamp/manual divergence is possible. Investigate first, then review the existing forward revision's creation path; preserve historical source. |
| `5d5e3ded4830`, compatible agendas | Verify UUID meeting PK, non-null final JSON, nullable JSONB suggestion, cascade FK to meetings, and owner FK on meetings; rehearse forward revision. Its existing checks alone do not validate all types/FKs. |
| `5d5e3ded4830`, incompatible agendas | Prepare a dedicated data-preserving transformation after reviewing existing metadata/data with authorized access. Existing forward revision deliberately stops for missing columns/key. |
| `0004_reviewed_agendas`, matching schema | No agenda migration needed; investigate history separately and verify application compatibility. |
| Any claimed revision with contradictory schema | Treat as drift; no automatic repair/stamp/reset. Snapshot and investigate. |

Inspector metadata can distinguish absence, empty history and multiple rows, but cannot prove whether
an operator used `stamp` versus a real migration. Review release records as well. No application
rows are fetched by this inspector. If existing data needs transformation, request narrowly scoped
additional read-only evidence rather than expanding the inspector into an arbitrary SQL endpoint.


## Target evidence from the authorized bounded diagnostic

The `891447916595/us-east-1/meetings-db` inspection succeeded: recorded revision `0003`,
no public `agendas` table, and validated meetings owner FK. See
[inspection report](lab6/database-inspection-report.md) and its sanitized JSON snapshot.
This selects the `0003, no agendas` decision-table row; it does not establish cross-environment
history. The candidate unapplied-only repair was rehearsed in a temporary source copy against
fresh disposable PostgreSQL 16 through head, successfully. Historical source remains unchanged.


## Release recommendation after observed-state rehearsal

See [final release plan](lab6/final-release-plan.md) for the recommended target-specific correction,
backup, deployment dependency ordering and approval boundaries. The repaired predecessor can run
additively on the inspected `0003`/absent-agendas database. The candidate remains a patch, not an
edit to the historical source in this preparation. Approving that correction preserves revision IDs
and graph, but changes the historical file checksum; do not describe it as a new forward revision.
The earlier globally-never-used condition is the conservative policy choice, not a fact established
by the current target inspection. Already-recorded revisions are skipped elsewhere; their actual
schema compatibility still must be reviewed before using this release there.

`0004_reviewed_agendas` now also rejects incompatible UUID/JSON/JSONB types, nullability and missing
cascade FK instead of silently accepting them. Local rehearsal reproduces revision 0003 with synthetic
users/meetings/participants/links and checks complete row fingerprints before/after upgrades, one
agenda index, PK/FK/nullability enforcement, cascade inside a rolled-back test, and repeat-upgrade
preservation of saved agendas. No existing cloud database is used by the rehearsal.


## Approved local correction applied

The owner subsequently authorized applying the prepared correction. Historical source is now
corrected locally, with revision/dependency IDs unchanged; the focused PostgreSQL rehearsal passed
again. No production migration has run. See `lab6/release-preparation.md` for current backup/artifact
state and the ECR lifecycle blocker. Earlier “unapplied patch” entries describe previous phases.
