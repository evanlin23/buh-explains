Set up YouTube upload access and a daily upload schedule for my @BuhExplains channel. I'll give you my existing Google OAuth Client ID and Client secret here in your chat. Use them only by pasting them into the OAuth Playground and into GitHub's secret fields. Secret values (client secret, refresh token, GitHub token) go from one page into another, nothing else. Never repeat them back in this chat, a GitHub issue, a commit or any other page. If anything doesn't match what I describe, stop and tell me instead of guessing.

1. OAuth Playground (https://developers.google.com/oauthplayground):
   a. Gear icon → tick "Use your own OAuth credentials" → paste my Client ID and Client secret. Set Access type: Offline, Force prompt: Consent Screen.
   b. In "Input your own scopes", paste exactly:
      https://www.googleapis.com/auth/youtube.upload https://www.googleapis.com/auth/youtube.readonly
      Click "Authorize APIs".
   c. When Google asks which account or channel to use, pick the **BuhExplains** channel (@BuhExplains), NOT Buhtown, Packed, Six Degrees or any other. If you can't tell which is which, stop and ask me. Click through the "Google hasn't verified this app" warning (Advanced → continue). It's my own app.
   d. Click "Exchange authorization code for tokens". Keep the Refresh token in this tab for step 3.
   e. Check: in Step 3, request GET https://www.googleapis.com/youtube/v3/channels?part=snippet&mine=true and confirm the channel title is "Buh Explains" (handle @BuhExplains). Note its "id" (it starts with UC). If it shows any other channel, start step 1 again and pick BuhExplains.

2. GitHub repo evanlin23/buh-explains → Settings → Actions → General → Workflow permissions: select "Read and write permissions" → Save.

3. GitHub repo evanlin23/buh-explains → Settings → Secrets and variables → Actions:
   - Secrets tab → New repository secret, three times:
     YT_CLIENT_ID = my client ID
     YT_CLIENT_SECRET = my client secret
     YT_REFRESH_TOKEN = the refresh token from step 1d
   - Variables tab → New repository variable:
     YT_CHANNEL_ID = the UC... id from step 1e
   - Do NOT create the variable YT_ENABLED. I'll turn uploads on myself, separately. Until then the daily job runs and does nothing.

4. A GitHub token for the cron service: GitHub → Settings → Developer settings → Personal access tokens → Fine-grained tokens. If a token named "cron-job.org dispatch" exists, edit it: under Repository access add evanlin23/buh-explains next to the repos already there, keep Repository permissions → Actions: Read and write, and save. (Editing doesn't change its value, so my existing cron-job.org jobs keep working.) Otherwise generate a new token named "cron-job.org buh-explains": Only select repositories → evanlin23/buh-explains, Repository permissions → Actions: Read and write, nothing else, 90 days.

5. cron-job.org (log into my existing account). If you edited the existing token in step 4, open my existing "blocky upload" job and use its Clone action (that copies the headers and token without anyone retyping them). Otherwise create a new job and paste the new token into the Authorization header. The job:
   - Title: buhexplains upload
   - URL: https://api.github.com/repos/evanlin23/buh-explains/actions/workflows/upload.yml/dispatches
   - Schedule: every day at 7:07, time zone America/Chicago
   - Advanced → Request method: POST
   - Headers: Accept: application/vnd.github+json, Authorization: Bearer <the token>, X-GitHub-Api-Version: 2022-11-28
   - Request body, exactly: {"ref":"main"}
   - Make sure the job is enabled (clones start disabled).
   - Press "Test run" once. A good result is HTTP 204. Uploads are still off (no YT_ENABLED), so it only runs the workflow, which prints "uploads are off" and does nothing.

6. Finish by telling me which steps you completed, the channel title you confirmed in step 1e, and the Test run's HTTP status. Don't include any secret values.
