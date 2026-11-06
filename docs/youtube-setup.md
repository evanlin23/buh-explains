# YouTube upload setup for @BuhExplains (one time, free)

Uploads are **off** until every step here is done. The `upload` workflow checks for all of them and otherwise prints "uploads are off" and does nothing. Adapted from blocky-stories' `docs/youtube-setup.md`.

## Status
- Step 1 is **already done**: reuse the Web OAuth client in the existing **blocky-stories** Google Cloud project (YouTube Data API v3 enabled, app published). Start at step 2.
- Steps 2 and 3, plus the cron-job.org daily schedule, can be done by the Claude browser extension: paste `docs/browser-setup-prompt.md` into it, then give it the Client ID and secret in its own chat. It stops before turning uploads on.
- **The daily clock:** cron-job.org dispatches `upload.yml` with no slug every day at 7:07 AM Central, on `main`. With no slug, the uploader takes the first episode in `buhexplains/queue.txt` (deadline order) that isn't uploaded yet, uploads at most one per Central day, and needs its `film-<slug>` artifact (from `render.yml`).

## 1. Google Cloud (console.cloud.google.com) (done: reuse blocky-stories' client)
1. Create a project (`buh-explains`). Skip any billing prompt.
2. APIs & Services → Library → **YouTube Data API v3** → Enable.
3. OAuth consent screen: External; add the scopes `youtube.upload` and `youtube.readonly`; add yourself as a test user; then **Publish app** (in Testing mode the token dies every 7 days).
4. Clients → Create OAuth client → **Web application**, redirect URI `https://developers.google.com/oauthplayground`.

## 2. Refresh token (browser only)
At https://developers.google.com/oauthplayground: gear icon → use your own OAuth credentials, Access type Offline, Force prompt Consent. Authorize those two scopes **as the @BuhExplains channel**, then exchange the code and copy the **refresh token**. Check it with `GET https://www.googleapis.com/youtube/v3/channels?part=snippet&mine=true` and note the channel `id` (UC...).

## 3. GitHub (this repo → Settings → Secrets and variables → Actions)
- **Secrets:** `YT_CLIENT_ID`, `YT_CLIENT_SECRET`, `YT_REFRESH_TOKEN` (and `GEMINI_API_KEY`, already there).
- **Variables:** `YT_CHANNEL_ID` = the UC... id. The upload refuses if the token belongs to any other channel.
- **Variable `YT_ENABLED` = `true`** turns uploads on. Delete it (or set anything else) to turn them off again.
- Actions → General → Workflow permissions: **Read and write**.

## 4. How a video goes up
1. Push an episode: the `voice` workflow makes the narration.
2. Run `render` with the slug: it makes the `film-<slug>` artifact.
3. Run `upload` with the slug: private upload, public on its own at about 4:00 PM Central (YT_AUTOPUBLISH=false keeps it private). An issue tells you it's up.
4. GitHub's own `schedule:` never fires for this owner, so a daily clock means cron-job.org dispatching `upload.yml` (see blocky-stories `docs/external-cron.md`).

Quota: 10,000 units a day; an upload costs about 1,600.
