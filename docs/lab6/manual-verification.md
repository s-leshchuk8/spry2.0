# Manual-assisted production verification

No browser extension is available; the assistant must not reconnect or claim live browser checks.
Use the signed-in application: https://d17yxyt8by6ov0.cloudfront.net/.

## Five evaluations

1. Open New meeting → Paste agenda / AI parser. Use the five exact inputs in
   [evaluation-cases.json](evaluation-cases.json), in order. Do not save cases 2–5.
2. For each case click Parse with AI once, wait for completion, and leave at least 30 seconds
   before the next click. Do not retry failures. Record local click time including timezone.
3. Before editing, capture `01-review.png` through `05-review.png`, showing the input and suggested
   fields (or the error). Scroll/capture a second image if topics/actions do not fit. Hide account
   names/emails, unrelated calendar entries, browser profiles and credentials.
4. For exact JSON, optionally open DevTools → Network, select only the POST to the parser Function
   URL, and copy its **Response** tab into `01-response.json` etc. Do not export HAR, copy request
   headers, or use Copy as cURL. Record HTTP status and synthetic request `today`/`tz` fields only.
   JSON is necessary for the original lab's raw-output deliverable; screenshots alone are insufficient.
5. Report case number, click time/timezone, displayed fields or error, and attach screenshots/response
   JSON. The assistant will validate and independently retrieve matching sanitized CloudWatch usage,
   latency and outcome. No need for the user to collect tokens manually.

## One approved synthetic save/reopen

Use case 1 if successful; if not, use the first successful case. Capture its original suggestions
first. Change the title to `LAB6 SYNTHETIC — reviewed pricing test` and correct one other field if
appropriate. Show a suggested badge disappearing on edit. Select Use reviewed agenda, choose an
explicit future start/end in the meeting form, and explicitly Create. Leave participants empty and
avoid invitations, external links or personal information. Do not change an existing meeting.
Close/reopen the new meeting, select Add / view agenda, verify corrected title, topics, owners,
durations/actions. Capture `06-saved-reopened.png`. Record the new synthetic meeting ID only.
Retain the record; no deletion is authorized. If saving fails, stop and report it; do not create duplicates.

## Ownership evidence

Automated `backend/tests/test_agenda_api.py::test_agenda_save_preserves_suggestion_and_owner`
passes for Claude/Nova/Gemini metadata: owner save/read preserves final agenda and original suggestion;
a different authenticated subject gets 404 on read/write and anonymous access gets 401.
This is automated local evidence, not live two-account proof.

Optional live check needs two accounts whose owners authorize testing. In account B's separate browser,
confirm the **known newly created synthetic meeting** is absent. Attempt to open its known details URL
only if the UI provides one. Absence from the list alone does not prove API isolation. For a conclusive
API check use the application's normal authenticated mechanism to request that specific synthetic ID
and expect 404; never copy tokens or enumerate unrelated IDs. A blocked write test requires a controlled
authorized test harness; otherwise retain automated write-isolation evidence and mark live write testing
unverified. Do not change Cognito or create users merely for this check.

## Screenshots and <=45-second video

Keep credentials/DevTools and unrelated records off screen. Record a new parse only if separately desired;
the approved five cases can supply the video without a sixth inference request. Prefer recording case 1:
0–8s New meeting / paste; 8–22s Parse / show suggestions; 22–30s edit one field;
30–40s Use reviewed agenda / explicit Create; 40–45s reopen saved agenda.
Prepare date/time inputs beforehand if possible. Do not splice failures into a fake successful flow.
If actual latency makes this exceed 45 seconds, prepare a concise genuine recording and explain timing;
do not fabricate speed or metrics. Capture deployment/log screenshots without user IDs or secret values.

## Submission capture

Store only sanitized synthetic evidence under docs/lab6/evidence/ (create it when files exist).
Needed: five raw responses, five review screenshots, one reopen screenshot, sanitized CloudWatch events,
and <=45s GIF/MP4 or its submission link. Instructor approval of Gemini and final Git commit/push remain manual.
