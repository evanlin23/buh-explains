# Operations: how the channel runs itself

Set up 2026-11-06. Times are US Central (America/Chicago).

## The daily schedule
| Time | What | Where it's configured |
|---|---|---|
| 7:07 AM | Upload the next video in `buhexplains/queue.txt`; public about noon | cron-job.org job **"buhexplains upload"** → `upload.yml` on `main` |
| 1:23 PM | The producer makes a new episode | Claude scheduled task **"BuhExplains: make a video (afternoon)"** (`trig_019TRe3qFnkTw1jJQqoDSMwK`) |
| 2:07 PM | Upload the next video; public about 6 PM | cron-job.org job **"buhexplains upload 2"** → `upload.yml` on `main` |
| 12:23 PM and 6:23 PM | Post the channel's first comment on any of our videos that just went public | cron-job.org jobs **"buhexplains comments"** and **"buhexplains comments 2"** → `comments.yml` on `main` (every upload run also does a catch-up) |
| 8:41 PM | The producer makes another episode | Claude scheduled task **"BuhExplains: make a video (evening)"** (`trig_013Qt73kb2xaNSNXciSV1WcV`) |

## The pieces
- **The producer** is a persistent Claude Code session, "BuhExplains daily producer" (`session_019n1tKEkGRKrN3GaLngZKVK`), created with this repo as its source. Each scheduled task wakes it with "Make today's BuhExplains video", and it follows `.claude/skills/buh-episode/SKILL.md` (its first message holds an older copy of the same steps; the skill wins). A run:
  1. Scouts and picks one meme.
  2. Makes `epNN-<slug>` with the full pipeline (one Gemini request).
  3. Runs `audit.py`.
  4. Fast-forwards `main`, adds the slug to `queue.txt`, dispatches `render.yml`, and adds the MP4 to the `videos` branch.

  It never uploads to YouTube itself.
- **The uploader** (`upload.yml` → `buhexplains/pipeline/upload.py`):
  - With no slug, it takes the first slug in `queue.txt` that isn't in `buhexplains/uploads.json`, at most **2 per Central day**.
  - It downloads that slug's newest `film-<slug>` artifact from `render.yml`, uploads it **private** with a scheduled publish (1st of the day about noon, 2nd about 6 PM), and refuses if the token's channel isn't `YT_CHANNEL_ID`.
  - It commits `uploads.json` to `main` and opens a GitHub issue.
- **The comment poster** (`comments.yml` → `buhexplains/pipeline/comment.py`) posts each episode's `package.json` → `first_comment` as the channel, once per video, after the video is public, and records `"commented": true` in `uploads.json`. YouTube's API can't pin. It needs the `youtube.force-ssl` scope on `YT_REFRESH_TOKEN`; without it, the run says "insufficient scope" and posts nothing.
- **cron-job.org** is the clock for uploads, because GitHub's own `schedule:` never fires for this owner. It's the same account and token as blocky-stories: the fine-grained token "cron-job.org dispatch" has Actions read/write on this repo.
- **Secrets and variables** (repo Settings → Secrets and variables → Actions):
  - secrets: `GEMINI_API_KEY`, `YT_CLIENT_ID`, `YT_CLIENT_SECRET`, `YT_REFRESH_TOKEN`
  - variables: `YT_CHANNEL_ID` = `UCT8qvwFwJJuaMnEZzjuTmzA` (Buh Explains), `YT_ENABLED` = `true`

  Setup steps: `docs/youtube-setup.md`, `docs/browser-setup-prompt.md`.

## Controls
- **Stop all uploads:** delete the repo variable `YT_ENABLED` (or set it to anything but `true`). The cron runs keep firing and do nothing.
- **Change what goes up next:** edit `buhexplains/queue.txt` on `main`. Time-critical topics go at the top; uploaded slugs are skipped automatically.
- **Upload one by hand:** run `upload` with a slug (Actions → upload → Run workflow → `main`). Hand uploads count toward the 2 per day.
- **Pause production:** disable the two Claude scheduled tasks (claude.ai scheduled tasks, or ask Claude to `update_trigger enabled=false`).
- **Re-render an episode:** run `render` with its slug on `main`. The uploader always uses the newest successful `film-<slug>`.

## Limits and known failure modes
- **Gemini free tier:** about 10 TTS requests a day. The producer uses 1 per episode (2 a day). Raw takes are reused from earlier voice artifacts on any branch, so unchanged scripts cost nothing. On a quota error the producer commits the script and stops; it gets voiced on the next run.
- **Claude usage limit:** scheduled tasks stop when the weekly limit is reached and can start late (blocky-stories saw up to about an hour). Uploads don't depend on Claude: the cron keeps posting from the queue.
- **YouTube API quota:** 10,000 units a day; an upload costs about 1,600, so 2 a day is about 3,200.
- **Artifacts expire** after 90 days (`film-*`) or 30 days (`voice`). Re-run `render` for anything older before it's uploaded.
- **A missing film:** if `render` never succeeded for a queued slug, that upload run fails with "no film-<slug> artifact". Run `render` for it.
