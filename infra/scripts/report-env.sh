#!/usr/bin/env bash
# Manage the report-builder's environment variables.
#   report-env.sh sync          copy all env vars (DB settings...) from the API Lambda
#   report-env.sh set KEY=VAL   add/replace one variable (used for the DLQ experiment)
#   report-env.sh unset KEY     remove one variable
set -euo pipefail

PROJECT="${PROJECT:-meetings}"
SRC="${BACKEND_FUNCTION:-$PROJECT-backend}"
DST="$PROJECT-report-builder"
cmd="${1:-sync}"
arg="${2:-}"

tmp="$(mktemp)"
trap 'rm -f "$tmp" "$tmp.src" "$tmp.dst"' EXIT

aws lambda get-function-configuration --function-name "$DST" \
  --query 'Environment.Variables' --output json > "$tmp.dst"
if [ "$cmd" = sync ]; then
  aws lambda get-function-configuration --function-name "$SRC" \
    --query 'Environment.Variables' --output json > "$tmp.src"
else
  echo '{}' > "$tmp.src"
fi

python3 - "$cmd" "$arg" "$tmp.src" "$tmp.dst" > "$tmp" <<'PY'
import json, sys
cmd, arg, src_f, dst_f = sys.argv[1:5]
src = json.load(open(src_f)) or {}
dst = json.load(open(dst_f)) or {}
if cmd == "sync":
    keep = {k: v for k, v in dst.items() if k in ("REPORTS_BUCKET", "FAIL_WEEK")}
    env = {**src, **keep}
elif cmd == "set":
    k, v = arg.split("=", 1)
    env = {**dst, k: v}
elif cmd == "unset":
    env = {k: v for k, v in dst.items() if k != arg}
else:
    sys.exit("usage: report-env.sh sync | set KEY=VAL | unset KEY")
print(json.dumps({"Variables": env}))
PY

aws lambda update-function-configuration --function-name "$DST" \
  --environment "file://$tmp" --query LastUpdateStatus --output text >/dev/null
aws lambda wait function-updated --function-name "$DST"
echo "report-builder environment: $cmd done"