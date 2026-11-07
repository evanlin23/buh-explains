Check that my YouTube upload app won't stop working after 7 days, and fix it if needed. Secret values (client secret, refresh token) go from one page into another, nothing else. Never repeat them back in this chat, a GitHub issue, a commit or any other page. If anything doesn't match what I describe, stop and tell me instead of guessing.

1. Google Cloud console (https://console.cloud.google.com), the project that owns the OAuth client used for @BuhExplains uploads (the same client blocky-stories uses):
   a. APIs & Services → OAuth consent screen (in the new UI: Google Auth Platform → Audience).
   b. Read "Publishing status". If it says **In production**, tell me and stop: nothing else is needed.
   c. If it says **Testing**: click **Publish app** → Confirm. It may say the app will need verification because of the YouTube scopes; that's fine for my own use (I'll see an "unverified app" warning when I sign in, and the 100-user cap doesn't matter). Do not submit anything for verification.

2. Only if you changed Testing → In production in step 1c, mint a fresh refresh token (tokens issued while in Testing still die after 7 days):
   a. OAuth Playground (https://developers.google.com/oauthplayground): gear icon → "Use your own OAuth credentials" → my Client ID and Client secret (I'll give them to you in this chat); Access type: Offline; Force prompt: Consent Screen.
   b. Scopes, exactly: https://www.googleapis.com/auth/youtube.upload https://www.googleapis.com/auth/youtube.readonly https://www.googleapis.com/auth/youtube.force-ssl → Authorize APIs.
   c. Pick the **BuhExplains** channel (@BuhExplains), nothing else. Click through "Google hasn't verified this app" (Advanced → continue).
   d. Exchange authorization code for tokens. Check with GET https://www.googleapis.com/youtube/v3/channels?part=snippet&mine=true that the title is "Buh Explains".
   e. GitHub repo evanlin23/buh-explains → Settings → Secrets and variables → Actions → Secrets → YT_REFRESH_TOKEN → Update → paste the new refresh token → Save.

3. Tell me: the publishing status you found, whether you changed it, and whether you updated YT_REFRESH_TOKEN. Nothing else.
