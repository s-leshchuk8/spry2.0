#!/usr/bin/env bash
# Run from the repo root, after extracting report-feature.tar.gz into it:
#   bash install-report.sh you@example.com
# Safe to run more than once.
set -euo pipefail

EMAIL="${1:-}"
[ -n "$EMAIL" ] || { echo "Usage: bash install-report.sh you@example.com"; exit 1; }
[ -f Makefile ] && [ -d backend/app ] && [ -f Makefile.reports ] && [ -f infra/reports.yaml ] || {
  echo "Run this in the repo root (the folder with Makefile and backend/) after extracting the archive."; exit 1; }

chmod +x infra/scripts/report-*.sh

# 1. The Makefile from the assignment says back/, the folder is backend/
sed -i -e 's#back/Dockerfile#backend/Dockerfile#' -e 's#--push back$#--push backend#' \
       -e 's#cd back #cd backend #' -e 's#\./back$#./backend#' Makefile

# 2. Remove an old aws-reports-deploy target if there is one (its recipe lines may use spaces)
if grep -q '^aws-reports-deploy:' Makefile; then
  cp Makefile Makefile.bak
  awk '/^\.PHONY: aws-reports-deploy/ {next} /^aws-reports-deploy:/ {skip=1; next}
       skip && (/^[ \t]/ || /^$/) {next} {skip=0; print}' Makefile.bak > Makefile
  echo "Removed the old aws-reports-deploy target (backup: Makefile.bak)"
fi

# 3. Include the new targets
grep -q '^-include Makefile.reports' Makefile || printf '\n-include Makefile.reports\n' >> Makefile

# 4. Recipient address
touch .env
grep -q '^REPORT_EMAIL=' .env || printf '\nREPORT_EMAIL=%s\n' "$EMAIL" >> .env

rm -f infra/reports.yml
echo; echo "Done. Check:  make help | grep report"
