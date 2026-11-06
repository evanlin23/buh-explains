Give my @BuhExplains upload token permission to post comments, and schedule the comment poster. I'll give you my existing Google OAuth Client ID and Client secret here in your chat. Use them only by pasting them into the OAuth Playground. Secret values (client secret, refresh token) go from one page into another, nothing else. Never repeat them back in this chat, a GitHub issue, a commit or any other page. If anything doesn't match what I describe, stop and tell me instead of guessing.

1. OAuth Playground (https://developers.google.com/oauthplayground):
   a. Gear icon → tick "Use your own OAuth credentials" → paste my Client ID and Client secret. Access type: Offline, Force prompt: Consent Screen.
   b. In "Input your own scopes", paste exactly:
      https://www.googleapis.com/auth/youtube.upload https://www.googleapis.com/auth/youtube.readonly https://www.googleapis.com/auth/youtube.force-ssl
      Click "Authorize APIs".
   c. Pick the **BuhExplains** channel (@BuhExplains), NOT any other channel. If you can't tell which is which, stop and ask me. Click through the "Google hasn't verified this app" warning (Advanced → continue).
   d. Click "Exchange authorization code for tokens". Keep the new Refresh token in this tab.
   e. Check: in Step 3, request GET https://www.googleapis.com/youtube/v3/channels?part=snippet&mine=true and confirm the title is "Buh Explains" with id UCT8qvwFwJJuaMnEZzjuTmzA. If not, start again and pick BuhExplains.

2. GitHub repo evanlin23/buh-explains → Settings → Secrets and variables → Actions → Secrets tab → YT_REFRESH_TOKEN → Update secret → paste the new refresh token from step 1d → Save. Change nothing else.

3. cron-job.org: open my "buhexplains upload" job → Clone. Change only:
   - Title: buhexplains comments
   - URL: https://api.github.com/repos/evanlin23/buh-explains/actions/workflows/comments.yml/dispatches
   - Schedule: every day at 12:23, time zone America/Chicago
   Keep POST, the same headers, and the Request body exactly {"ref":"main"}. Enable it (clones start disabled).
   Then clone "buhexplains comments" once more and change only the Title to "buhexplains comments 2" and the Schedule to every day at 18:23 (6:23 PM). Enable it.
   Press "Test run" once on "buhexplains comments" (it only posts comments on our videos that are already public). Tell me the HTTP status (expected 204).

4. Finish by telling me which steps you completed, the channel title you confirmed in step 1e, and the Test run's status. Don't include any secret values.
