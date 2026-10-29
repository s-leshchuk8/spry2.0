#!/usr/bin/env bash
# Future approved read-only AWS operation. Writes a private local backup, never changes S3.
set -euo pipefail
cd "$(dirname "$0")/../.."
source infra/scripts/aws-target.sh
aws_target_init
backup="${1:?Supply a NEW private local backup directory}"
[ ! -e "$backup" ] || { echo 'Backup directory exists; refusing to overwrite'; exit 1; }
umask 077
mkdir -p "$backup/site"
aws_spry s3 sync s3://meetings-frontend-sitebucket-la6ugmfuat3e "$backup/site" --only-show-errors
for function in meetings-backend meetings-agenda-parser; do
  aws_spry lambda get-function --function-name "$function" \
    --query '{image:Code.ResolvedImageUri,architecture:Configuration.Architectures}' --output json > "$backup/$function.json"
done
aws_spry cloudformation get-template --stack-name meetings-ai --output json > "$backup/parser-template.json"
python3 - "$backup" <<'PY'
from pathlib import Path
import hashlib, json, sys
root = Path(sys.argv[1])
if not (root/'site/index.html').is_file():
    raise SystemExit('Backup incomplete: missing index.html; do not publish')
files = {str(p.relative_to(root/'site')): hashlib.sha256(p.read_bytes()).hexdigest()
         for p in sorted((root/'site').rglob('*')) if p.is_file()}
(root/'site-sha256.json').write_text(json.dumps(files, indent=2))
print('Backup completed; verify and retain it before any publish/delete operation.')
PY
