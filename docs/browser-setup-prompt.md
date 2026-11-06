Set up YouTube upload access for my @BuhExplains channel, reusing the Google Cloud OAuth client I already set up for blocky-stories. Do the steps in order. Secret values (client secret, refresh token) are copied from one page and pasted into another, nothing else. Never type them into this chat, a GitHub issue, a commit or any other page. If anything doesn't match what I describe, stop and tell me instead of guessing.

1. Google Cloud (console.cloud.google.com): open my existing "blocky-stories" project → APIs & Services (Google Auth Platform) → Clients. Open the existing Web OAuth client whose authorized redirect URI is https://developers.google.com/oauthplayground. Keep the tab open so you can copy its Client ID and Client secret in steps 2 and 4. Change nothing here.

2. OAuth Playground (https://developers.google.com/oauthplayground):
   a. Gear icon → tick "Use your own OAuth credentials" → paste that Client ID and Client secret. Set Access type: Offline, Force prompt: Consent Screen.
   b. In "Input your own scopes", paste exactly:
      https://www.googleapis.com/auth/youtube.upload https://www.googleapis.com/auth/youtube.readonly
      Click "Authorize APIs".
   c. When Google asks which account or channel to use, pick the **BuhExplains** channel (@BuhExplains), NOT Buhtown, Packed, Six Degrees or any other. If you can't tell which is which, stop and ask me. Click through the "Google hasn't verified this app" warning (Advanced → continue). It's my own app.
   d. Click "Exchange authorization code for tokens". Keep the Refresh token in this tab for step 4.
   e. Check: in Step 3, request GET https://www.googleapis.com/youtube/v3/channels?part=snippet&mine=true and confirm the channel title is "Buh Explains" (handle @BuhExplains). Note its "id" (it starts with UC). If it shows any other channel, start step 2 again and pick BuhExplains.

3. GitHub repo evanlin23/buh-explains → Settings → Actions → General → Workflow permissions: select "Read and write permissions" → Save.

4. GitHub repo evanlin23/buh-explains → Settings → Secrets and variables → Actions:
   - Secrets tab → New repository secret, three times:
     YT_CLIENT_ID = the client ID from step 1
     YT_CLIENT_SECRET = the client secret from step 1
     YT_REFRESH_TOKEN = the refresh token from step 2d
   - Variables tab → New repository variable:
     YT_CHANNEL_ID = the UC... id from step 2e
   - Do NOT create the variable YT_ENABLED. I'll turn uploads on myself, separately.

5. Finish by telling me which steps you completed and the channel title you confirmed in step 2e. Don't include any secret values.
