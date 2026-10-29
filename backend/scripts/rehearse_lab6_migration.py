"""Local-only rehearsal: own disposable PostgreSQL container, temporary patched source.

Never accepts AWS credentials or an external database URL. Requires existing postgres:16-alpine.
Does not change repository migration files. Removes only its own labelled container/volumes.
"""

import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from uuid import uuid4

ROOT = Path(__file__).resolve().parents[2]


def run(args, **kwargs):
    return subprocess.run(args, check=True, text=True, capture_output=True, **kwargs).stdout


def main():
    name = "spry-rehearsal-" + uuid4().hex[:12]
    owner = uuid4().hex
    run(["docker", "image", "inspect", "postgres:16-alpine"])
    run(
        [
            "docker",
            "run",
            "-d",
            "--name",
            name,
            "--label",
            f"spry.rehearsal={owner}",
            "-e",
            "POSTGRES_HOST_AUTH_METHOD=trust",
            "-e",
            "POSTGRES_DB=spry_lab6_disposable",
            "-p",
            "127.0.0.1::5432",
            "postgres:16-alpine",
        ]
    )
    try:
        for _ in range(40):
            ready = subprocess.run(
                ["docker", "exec", name, "pg_isready", "-U", "postgres"], capture_output=True
            )
            if ready.returncode == 0:
                break
            time.sleep(0.5)
        else:
            raise RuntimeError("Disposable PostgreSQL startup failed")
        info = json.loads(run(["docker", "inspect", name]))[0]
        port = info["NetworkSettings"]["Ports"]["5432/tcp"][0]["HostPort"]
        env = dict(os.environ)
        # Override all database routing; no shared or production database is reachable by this script.
        env.update(
            DATABASE_URL=f"postgresql+psycopg://postgres@127.0.0.1:{port}/spry_lab6_disposable",
            PYTHONPATH=str(ROOT / "backend"),
            PGOPTIONS="-c statement_timeout=10000 -c lock_timeout=3000",
        )
        with tempfile.TemporaryDirectory(prefix="spry-migration-source-") as directory:
            work = Path(directory)
            shutil.copytree(ROOT / "backend/alembic", work / "alembic")
            ini = (
                (ROOT / "backend/alembic.ini")
                .read_text()
                .replace("script_location = alembic", f"script_location = {work / 'alembic'}")
            )
            (work / "alembic.ini").write_text(ini)
            patch = (ROOT / "docs/migration-repairs/unapplied-only.patch").read_text()
            patch = patch.replace("a/backend/", "a/").replace("b/backend/", "b/")
            patchable = subprocess.run(
                ["patch", "--batch", "--forward", "--dry-run", "-p1"],
                cwd=work,
                input=patch,
                text=True,
                capture_output=True,
            )
            if patchable.returncode == 0:
                run(["patch", "--batch", "--forward", "-p1"], cwd=work, input=patch)
            else:
                # Accept only the exact already-applied candidate, not an unknown historical edit.
                run(["patch", "--batch", "--dry-run", "-R", "-p1"], cwd=work, input=patch)
            alembic = [sys.executable, "-m", "alembic", "-c", str(work / "alembic.ini")]
            run([*alembic, "upgrade", "0003"], env=env)

            def sql(statement):
                return run(
                    [
                        "docker",
                        "exec",
                        "-i",
                        name,
                        "psql",
                        "-X",
                        "-v",
                        "ON_ERROR_STOP=1",
                        "-U",
                        "postgres",
                        "-d",
                        "spry_lab6_disposable",
                        "-At",
                    ],
                    input=statement,
                )

            sql("""
INSERT INTO users (id,cognito_sub,email,name)
VALUES ('11111111-1111-1111-1111-111111111111','local-rehearsal','test@example.test','Test');
INSERT INTO meetings (id,title,description,starts_at,ends_at,owner_id)
VALUES ('22222222-2222-2222-2222-222222222222','Existing meeting','Preserve this',
'2026-10-29 10:00Z','2026-10-29 11:00Z','11111111-1111-1111-1111-111111111111'),
('33333333-3333-3333-3333-333333333333','Legacy ownerless',NULL,
'2026-10-29 12:00Z','2026-10-29 13:00Z',NULL);
INSERT INTO participants(id,name,email)
VALUES ('44444444-4444-4444-4444-444444444444','Participant','participant@example.test');
INSERT INTO meeting_participants VALUES
('22222222-2222-2222-2222-222222222222','44444444-4444-4444-4444-444444444444');
""")
            fingerprint = """SELECT md5(string_agg(x,'|' ORDER BY x)) FROM (
SELECT 'users:'||row_to_json(t)::text x FROM users t UNION ALL
SELECT 'meetings:'||row_to_json(t)::text FROM meetings t UNION ALL
SELECT 'participants:'||row_to_json(t)::text FROM participants t UNION ALL
SELECT 'links:'||row_to_json(t)::text FROM meeting_participants t) rows;
"""
            before = sql(fingerprint)
            assert sql("SELECT version_num FROM alembic_version;").strip() == "0003"
            assert sql("SELECT to_regclass('public.agendas') IS NULL;").strip() == "t"
            run([*alembic, "upgrade", "0004_reviewed_agendas"], env=env)
            assert sql(fingerprint) == before
            assert sql("SELECT version_num FROM alembic_version;").strip() == "0004_reviewed_agendas"
            assert sql("""SELECT string_agg(column_name||':'||udt_name||':'||is_nullable,','
ORDER BY ordinal_position)
FROM information_schema.columns WHERE table_schema='public' AND table_name='agendas';""").strip() == (
                "meeting_id:uuid:NO,final_agenda:json:NO,ai_suggestion:jsonb:YES"
            )
            assert (
                sql("""SELECT count(*) FROM pg_constraint WHERE conrelid='agendas'::regclass
AND contype='f' AND confrelid='meetings'::regclass AND confdeltype='c' AND convalidated;""").strip()
                == "1"
            )
            assert sql("SELECT count(*) FROM pg_indexes WHERE tablename='agendas';").strip() == "1"
            sql("""INSERT INTO agendas VALUES ('22222222-2222-2222-2222-222222222222',
'{"title":"reviewed"}', '{"original":"suggestion"}');""")
            agenda = sql("SELECT row_to_json(t) FROM agendas t;")
            run([*alembic, "upgrade", "0004_reviewed_agendas"], env=env)
            assert sql(fingerprint) == before
            assert sql("SELECT row_to_json(t) FROM agendas t;") == agenda
            assert sql("SELECT count(*) FROM pg_indexes WHERE tablename='agendas';").strip() == "1"
            sql("""BEGIN;
DO $$ BEGIN
BEGIN INSERT INTO agendas VALUES ('22222222-2222-2222-2222-222222222222','{}',NULL);
RAISE EXCEPTION 'Duplicate accepted'; EXCEPTION WHEN unique_violation THEN NULL; END;
BEGIN INSERT INTO agendas VALUES ('55555555-5555-5555-5555-555555555555','{}',NULL);
RAISE EXCEPTION 'Orphan accepted'; EXCEPTION WHEN foreign_key_violation THEN NULL; END;
BEGIN INSERT INTO agendas VALUES ('33333333-3333-3333-3333-333333333333',NULL,NULL);
RAISE EXCEPTION 'Null agenda accepted'; EXCEPTION WHEN not_null_violation THEN NULL; END;
END $$;
DELETE FROM meetings WHERE id='22222222-2222-2222-2222-222222222222';
DO $$ BEGIN IF EXISTS (SELECT 1 FROM agendas) THEN RAISE EXCEPTION 'Cascade failed'; END IF; END $$;
ROLLBACK;""")
            assert sql(fingerprint) == before and sql("SELECT row_to_json(t) FROM agendas t;") == agenda
            test_env = dict(env, SPRY_DISPOSABLE_TEST_DATABASE_URL=env["DATABASE_URL"])
            print(
                run(
                    [
                        sys.executable,
                        "-m",
                        "pytest",
                        str(ROOT / "backend/tests/test_agenda_migrations.py"),
                        "-q",
                        "--tb=short",
                    ],
                    env=test_env,
                )
            )
            print(
                "PASS: observed 0003/absent-agendas -> head; existing data byte-equivalent; "
                "types/PK/FK/cascade/nullability; repeat upgrade preserves agenda and indexes"
            )
    finally:
        info = json.loads(run(["docker", "inspect", name]))[0]
        assert info["Config"]["Labels"]["spry.rehearsal"] == owner
        run(["docker", "rm", "-fv", name])
        print("Removed owned disposable container and volumes")


if __name__ == "__main__":
    main()
