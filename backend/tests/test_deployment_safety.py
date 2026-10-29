"""CLI integration tests use ONLY fake executables; no AWS/registry calls occur."""

import json
import os
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).parents[2]
FAKE_AWS = """#!/usr/bin/env python3
import sys,os,json
from pathlib import Path
args=sys.argv[1:]
with open(os.environ['FAKE_AWS_LOG'],'a') as f: f.write(json.dumps(args)+'\\n')
assert args[args.index('--profile')+1]=='spry-friend'
assert args[args.index('--region')+1]=='us-east-1'
def out(x): print(json.dumps(x))
if 'get-caller-identity' in args: print(os.environ.get('FAKE_ACCOUNT','891447916595'))
elif 'describe-secret' in args:
 out({'arn':os.environ['GEMINI_API_KEY_SECRET_ARN'],
      'tags':[{'Key':'PROJECT_NAME','Value':'meetings'}],
      'deleted':None,'versions':{'v1':['AWSCURRENT']}})
elif 'describe-images' in args: print('sha256:'+'a'*64)
elif 'get-account-settings' in args: print('10')
elif 'describe-stacks' in args: print('UPDATE_COMPLETE')
elif 'describe-log-groups' in args: out(['/aws/lambda/meetings-agenda-parser'])
elif 'describe-budget' in args: out({'amount':'5','unit':'USD','period':'MONTHLY'})
elif 'get-function-configuration' in args:
 if '--query' in args: out({'cors':'https://example.test','region':'us-east-1','pool':'pool','client':'client'})
 else: out({'Role':'arn:aws:iam::891447916595:role/meetings-backend-BackendRole-test',
            'Architectures':['arm64'],
            'VpcConfig':{'VpcId':'vpc-095d43a8e0d6631c5',
                         'SubnetIds':['subnet-test'],'SecurityGroupIds':['sg-test']},
            'Environment':{'Variables':{'DB_HOST':'test.us-east-1.rds.amazonaws.com','DB_PORT':'5432','DB_USER':'test',
                                        'DB_PASSWORD':'fake-private-value','DB_NAME':'meetings','COGNITO_CLIENT_ID':'not-copied'}}})
elif 'deploy' in args:
 path=args[args.index('--parameter-overrides')+1].replace('file://','')
 params=json.load(open(path))
 with open(os.environ['FAKE_PARAMS'],'w') as f: json.dump(params,f)
 print('preview')
elif 'create-function' in args:
 cfg=json.load(open(args[args.index('--cli-input-json')+1].replace('file://','')))
 cfg['Environment']={'keys':sorted(cfg['Environment']['Variables'])}
 with open(os.environ['FAKE_PARAMS'],'w') as f: json.dump(cfg,f)
 print('meetings-db-inspection-lab6')
elif 'wait' in args: pass
elif 'list-tags' in args:
 out({'Tags':{'PROJECT_NAME':'meetings',
               'PURPOSE':os.environ.get('FAKE_PURPOSE','lab6-readonly-inspection')}})
elif 'delete-function' in args: pass
else: raise SystemExit('Unexpected fake command: '+str(args))
"""


@pytest.fixture
def cli(tmp_path):
    tools = tmp_path / "bin"
    tools.mkdir()
    (tools / "aws").write_text(FAKE_AWS)
    (tools / "aws").chmod(0o755)
    (tools / "docker").write_text(
        "#!/usr/bin/env python3\nimport json,os\n"
        'print(json.dumps({"architecture":os.environ.get("FAKE_ARCH","arm64")}))\n'
    )
    (tools / "docker").chmod(0o755)
    env = {k: v for k, v in os.environ.items() if not k.startswith("AWS_") and k != "AI_EXECUTE"}
    env.update(
        PATH=f"{tools}:{env['PATH']}",
        FAKE_AWS_LOG=str(tmp_path / "calls"),
        FAKE_PARAMS=str(tmp_path / "params"),
        AI_IMAGE_URI="891447916595.dkr.ecr.us-east-1.amazonaws.com/meetings-backend:reviewed",
        AI_LAMBDA_ARCH="arm64",
        PROJECT="meetings",
        PARSER_CONCURRENCY="0",
        EXISTING_BUDGET_NAME="meetings-monthly-5usd",
        GEMINI_API_KEY_SECRET_ARN="arn:aws:secretsmanager:us-east-1:891447916595:secret:meetings/gemini-api-key-ABC123",
    )
    return env, tmp_path


def run(script, env, *args):
    return subprocess.run(
        ["bash", str(ROOT / "infra/scripts" / script), *args],
        env=env,
        capture_output=True,
        text=True,
        cwd=ROOT,
    )


def calls(path):
    return [json.loads(line) for line in (path / "calls").read_text().splitlines()]


def test_wrong_account_stops_before_other_operations(cli):
    env, path = cli
    env["FAKE_ACCOUNT"] = "968053399627"
    result = run("ai-deploy.sh", env)
    assert result.returncode != 0
    assert len(calls(path)) == 1 and "get-caller-identity" in calls(path)[0]


def test_credential_override_stops_before_any_aws_call(cli):
    env, path = cli
    env["AWS_ACCESS_KEY_ID"] = "fake-override"
    result = run("ai-deploy.sh", env)
    assert result.returncode != 0 and not (path / "calls").exists()
    assert "fake-override" not in result.stdout + result.stderr


def test_parser_previews_and_never_copies_db_settings(cli):
    env, path = cli
    result = run("ai-deploy.sh", env)
    assert result.returncode == 0, result.stderr
    deploy = next(c for c in calls(path) if "deploy" in c)
    assert "--no-execute-changeset" in deploy
    assert not any("delete-stack" in c or "create-budget" in c for c in calls(path))
    params = {p["ParameterKey"]: p["ParameterValue"] for p in json.loads((path / "params").read_text())}
    assert params["ParserConcurrency"] == "0"
    assert params["Architecture"] == "arm64"
    assert params["ParserModel"] == "gemini-3.5-flash-lite"
    assert params["PromptVersion"] == "agenda-v2-gemini"
    assert params["GeminiApiKeySecretArn"] == env["GEMINI_API_KEY_SECRET_ARN"]
    assert not any("get-secret-value" in c for c in calls(path))
    assert params["ExistingBudgetName"] == "meetings-monthly-5usd"
    query = next(c for c in calls(path) if "get-function-configuration" in c)
    assert "--query" in query and "DB_" not in query[query.index("--query") + 1]


def test_wrong_image_architecture_cannot_deploy(cli):
    env, path = cli
    env["FAKE_ARCH"] = "amd64"
    assert run("ai-deploy.sh", env).returncode != 0
    assert not any("deploy" in c for c in calls(path))


def test_inspector_is_private_and_does_not_change_backend(cli):
    env, path = cli
    env["INSPECT_IMAGE_URI"] = (
        "891447916595.dkr.ecr.us-east-1.amazonaws.com/meetings-backend@sha256:" + "a" * 64
    )
    result = run("db-inspect.sh", env, "create")
    assert result.returncode == 0, result.stderr
    cfg = json.loads((path / "params").read_text())
    assert cfg["FunctionName"] == "meetings-db-inspection-lab6"
    assert cfg["ImageConfig"]["Command"] == ["app.diagnostics.db_inspection.handler"]
    assert cfg["Environment"]["keys"] == ["DB_HOST", "DB_NAME", "DB_PASSWORD", "DB_PORT", "DB_USER"]
    assert not any(
        any(
            w in c for w in ["invoke", "update-function-code", "add-permission", "create-function-url-config"]
        )
        for c in calls(path)
    )
    assert "fake-private-value" not in result.stdout + result.stderr


def test_inspector_cleanup_requires_ownership_tag(cli):
    env, path = cli
    env["FAKE_PURPOSE"] = "unrelated"
    assert run("db-inspect.sh", env, "remove").returncode != 0
    assert not any("delete-function" in c for c in calls(path))


def test_low_quota_cannot_enable_reservation(cli):
    env, path = cli
    env["PARSER_CONCURRENCY"] = "2"
    assert run("ai-deploy.sh", env).returncode != 0
    assert not any("deploy" in c for c in calls(path))


@pytest.mark.parametrize("profile", ["", "default"])
def test_empty_or_default_profile_cannot_fall_back(cli, profile):
    env, path = cli
    env["AWS_PROFILE"] = profile
    assert run("ai-deploy.sh", env).returncode != 0
    assert not (path / "calls").exists()


def test_parser_requires_exact_secret_arn(cli):
    env, path = cli
    env.pop("GEMINI_API_KEY_SECRET_ARN")
    assert run("ai-deploy.sh", env).returncode != 0
    assert not any("deploy" in c for c in calls(path))


def test_gemini_template_has_only_secret_read_permission():
    import yaml

    class Loader(yaml.SafeLoader):
        pass

    Loader.add_constructor("!Ref", lambda loader, node: {"Ref": loader.construct_scalar(node)})
    Loader.add_constructor("!Sub", lambda loader, node: {"Sub": loader.construct_scalar(node)})
    Loader.add_multi_constructor("!", lambda loader, tag, node: None)
    template = yaml.load((ROOT / "infra/ai.yml").read_text(), Loader=Loader)
    resources = template["Resources"]
    statement = resources["AgendaParserRole"]["Properties"]["Policies"][0]["PolicyDocument"]["Statement"]
    assert statement == [
        {
            "Effect": "Allow",
            "Action": "secretsmanager:GetSecretValue",
            "Resource": {"Ref": "GeminiApiKeySecretArn"},
        }
    ]
    env = resources["AgendaParserFunction"]["Properties"]["Environment"]["Variables"]
    assert env["GEMINI_API_KEY_SECRET_ARN"] == {"Ref": "GeminiApiKeySecretArn"}
    assert "GEMINI_API_KEY" not in env and env["PARSER_MOCK"] == "0"
    assert not any(
        r["Type"].startswith(("AWS::Budgets::", "AWS::Logs::", "AWS::SecretsManager::"))
        for r in resources.values()
    )
