---
name: buh-status
description: Check that the @BuhExplains automation is healthy - today's uploads, publish times, first comments, the producer's runs, renders and the queue buffer. Use when asked "what's going up", "did it upload", "is everything running", or on a check-in.
---

# BuhExplains status check

Times are US Central. Schedule and controls: `docs/operations.md`.

1. `git fetch origin main` and read `buhexplains/uploads.json` (video_id, publish_at UTC, `commented`) and `buhexplains/queue.txt`.
2. Uploads: the 7:07 AM and 2:07 PM cron-job.org jobs run `upload.yml` on main. If a slot passed with no new uploads.json entry, check `upload.yml` runs (GitHub MCP `list_workflow_runs`, then job logs). No run at all = cron-job.org didn't fire (owner fixes it there); a failed run = read the log ("no film-<slug> artifact" → dispatch `render.yml` for it; "insufficient scope"/auth → owner re-authorizes per `docs/youtube-setup.md`).
3. Comments: videos past `publish_at` should have `"commented": true` after the 12:23/6:23 PM `comments.yml` runs.
4. Production: new `epNN` commits on main from the producer session (`session_019n1tKEkGRKrN3GaLngZKVK`, runs 1:23 PM and 8:41 PM). `get_session` / `list_events` with `kinds: ["assistant","result"]` and a small limit (full transcripts are huge).
5. Films: every pending queue slug needs a successful `film-<slug>` (artifacts expire after 90 days).
6. Buffer: pending slugs ÷ 2 = days of uploads left. Under 4 days → run /buh-episode or /buh-scout for evergreen buffer.
7. Report in plain words: what's public/scheduled today and tomorrow (title + time), anything broken and who needs to fix it. Never upload by hand or edit cron/scheduled tasks unless the owner says so.
