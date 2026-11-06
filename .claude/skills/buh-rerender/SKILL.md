---
name: buh-rerender
description: Apply a pipeline change to every not-yet-uploaded @BuhExplains episode - re-render the queue on Actions, spot-check, and refresh the videos branch. Use after any change to render.py/voice.py/the look, or when owner feedback should reach the queued videos.
---

# Re-render the queue

1. Owner feedback first: add it to `buhexplains/PLAYBOOK.md` → Owner notes as a dated quote, in the same commit as the fix (CLAUDE.md rule). Test the fix locally on one episode (`buhexplains/make.sh <slug>`; symlink `.cache`/`out` from the main checkout if you're in a worktree, and remove the symlinks before committing) and compare frames before/after.
2. Push the fix to `main` (fast-forward). If no `lines` text changed, add `[skip ci]` so `voice.yml` doesn't run.
3. Pending slugs = lines of `buhexplains/queue.txt` (strip comments) minus the keys of `buhexplains/uploads.json`. Uploaded videos are never re-rendered or replaced.
4. Dispatch `render.yml` on ref `main` for each pending slug (GitHub MCP `actions_run_trigger`, inputs `{"slug": ...}`). Runs take 5–10 min; an apt/ffmpeg install sometimes hangs for 30+ min, which only delays that run.
5. When they finish: list each run's artifact (`list_workflow_run_artifacts`), get a download URL (`download_workflow_run_artifact`, expires in ~10 min, so curl right away), and check: 1080x1920, bitrate, a contact sheet of the next one to upload, and `audit.py` (it reads `out/<slug>/`; point `audit.REPO` at a scratch dir holding `out/<slug>/<slug>.mp4` and `words.json`).
6. Copy the MP4s into the `videos` branch worktree, commit as evanlin23, push.
7. Tell the owner what changed, which episodes got it, and anything that couldn't be fixed.
