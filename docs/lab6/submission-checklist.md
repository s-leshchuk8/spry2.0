# Lab 6 submission checklist

- [x] Deployed Gemini parser / authenticated real suggestions verified.
- [x] Sanitized real usage/latency log; deployment and $5-budget evidence saved.
- [x] All 156 disposable-PostgreSQL backend tests / 47 frontend tests pass; style/build/infra checks pass.
- [x] ADR, C4 diagram, substitution/security/cost notes and manual/video instructions prepared.
- [x] Automated owner isolation and final/original suggestion persistence pass.
- [ ] Run five UI cases once each; preserve actual JSON, screenshots, time/timezone and errors.
- [ ] Correlate those five cases with sanitized CloudWatch metrics; finalize accuracy/invention table.
- [ ] Complete observed-outcome Step 5 answers using actual results.
- [ ] Save/reopen one clearly labelled synthetic meeting; capture confirmation screenshot.
- [ ] Optional live two-authorized-account isolation; until then label it unverified.
- [ ] Record deployed <=45s GIF/MP4 showing paste, parse, edit one field, explicit save/reopen.
- [ ] Obtain instructor approval for Gemini instead of required Claude/Bedrock tool extraction.
- [ ] Final Git review includes untracked Lab 6 source/tests/docs/infra, excludes credentials,
  local editor settings, generated caches and dependency/build directories. Preserve source/evidence.
- [ ] User approves commit/push; attach actual commit link and media/evaluation/log/ADR to submission.

Do not mark pending items complete based on unit tests or the single prior smoke. No submission,
commit, push, destructive cleanup or new AWS resources are authorized by this checklist.

- [ ] Approve/publish the frontend-only saved-agenda visibility fix, then inspect the existing synthetic
  meeting via Edit meeting → View agenda. Do not create a duplicate or re-run the parser.
  [Plan](saved-agenda-fix.md); specific production agenda persistence remains unconfirmed until readback.
