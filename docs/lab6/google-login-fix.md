# Google redirect_uri_mismatch — verified configuration and minimal repair

Account verified read-only: spry-friend / 891447916595 / us-east-1. No authentication settings,
resources, application data or frontend assets were modified during this investigation.

## Observed redirect chain

1. Live frontend `https://d17yxyt8by6ov0.cloudfront.net` uses Cognito client
   `1khhpp0nuj0qc9qflnfc9ao5h6` and domain
   `meetings-891447916595.auth.us-east-1.amazoncognito.com`; fetched deployed JS confirms both.
2. Frontend requests Cognito authorization using callback
   `https://d17yxyt8by6ov0.cloudfront.net/auth/callback`.
   That exact callback is registered on the live app client. Google is a supported provider;
   authorization code flow and openid/email/profile scopes are enabled.
3. A read-only request to Hosted UI /oauth2/authorize returned HTTP 302 to accounts.google.com.
   Captured redirect_uri is exactly:
   `https://meetings-891447916595.auth.us-east-1.amazoncognito.com/oauth2/idpresponse`.
4. Both the Cognito Google provider and the outbound Google request use this Google OAuth client:
   `957829014233-5o94i4cp5cqojdl56ujalvaip7u1s85i.apps.googleusercontent.com`.

The two callback URLs serve different legs. The frontend /auth/callback is correct in Cognito;
Google must authorize Cognito's /oauth2/idpresponse endpoint. No frontend/Cognito defect was found.
Given the reported Google redirect_uri_mismatch, the configured Google client's allowlist does not
match the actual URI. The current Google Cloud authorized-URI list is not readable through AWS and
was not independently inspected; do not invent its existing entries or assume which old domain it has.
If this is not the intended Google OAuth client, review that ownership/configuration separately
before changing Cognito; no client or pool should be recreated merely to fix a redirect allowlist.

## Manual repair by the Google project owner

1. Open https://console.cloud.google.com/auth/clients and select the project that owns the exact
   Google OAuth client ID above. Older UI: APIs & Services -> Credentials -> OAuth 2.0 Client IDs.
2. Open that existing Web application client.
3. Under **Authorized redirect URIs**, add exactly:

   `https://meetings-891447916595.auth.us-east-1.amazoncognito.com/oauth2/idpresponse`

   No trailing slash. Add to redirect URIs, not merely Authorized JavaScript origins.
   Preserve all existing entries and the existing client ID/secret.
4. Save. Allow time for Google configuration propagation, then start a fresh sign-in from the app.
   No Spry build, AWS update, Cognito recreation or Google client recreation is needed for this fix.

No Google changes were performed by this investigation. It requires manual Google Cloud access.

## Verification

Start from the deployed frontend, click Google, choose an existing permitted/test account and finish
consent. Expect Google -> Cognito /oauth2/idpresponse -> frontend /auth/callback -> signed-in app.
Check that redirect_uri_mismatch is gone, token exchange succeeds and existing meetings can be read.
Do not share authorization codes, tokens, client secrets or unredacted browser network captures.
No model invocation is needed. Actual successful Google login remains unverified until the owner
saves the allowlist change and completes sign-in.

References:
- https://docs.aws.amazon.com/cognito/latest/developerguide/federation-endpoints.html
- https://developers.google.com/identity/protocols/oauth2/web-server#redirect-uri-mismatch
