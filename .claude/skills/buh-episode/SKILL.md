---
name: buh-episode
description: Make one @BuhExplains Short end to end (scout, script, pictures, Gemini voice via Actions, render, audit, ship to main + queue + videos branch). Use when asked to make a BuhExplains video/episode, and on every producer run ("Make today's BuhExplains video").
---

# Make one BuhExplains episode

Read first: `CLAUDE.md`, `buhexplains/PLAYBOOK.md` (every owner note is binding and outranks everything except accuracy), `buhexplains/reference/TUNG_BREAKDOWN.md`, `docs/operations.md`. Copy the structure of the newest finished episode in `buhexplains/episodes/` rather than inventing a format.

## 1. Branch and claim a number
`git fetch origin main && git checkout -B daily/<YYYY-MM-DD> origin/main`. Commit as evanlin23 (`git config user.name evanlin23; git config user.email 113861384+evanlin23@users.noreply.github.com`). Take the next free `epNN`; if two sessions might run at once, push an empty `buhexplains/episodes/epNN-<slug>/` claim to main early.

## 2. Pick the topic
Run /buh-scout (or use an unmade pitch from the newest `buhexplains/pitches/` file). Prefer time-critical topics and a story shape the last 3 episodes didn't use.

## 3. Write it (`buhexplains/episodes/epNN-<slug>/`)
- `script.md`: facts with two sources (one primary). Held reveal: the hook is a question, the answer lands after 70% and never in the title. Years written as spoken. The narrator says names (`voice.bites: false`). Length varies, about 20–35 s.
- `episode.json`: `lines` with `beats` (img/fit/enter, stickers with `target`, labels, flash, punch, sfx), `images` with `url`, `page`, optional `crop`/`focus`, and `points` for every sticker target. `music` = the phonk bed used by recent episodes. `voice` = gemini Achird.
- **Pictures:** at least 1000 px on the long side (YouTube `maxresdefault`, Wikimedia/Fandom original-file URLs, `/originals/` paths). Nothing under 600 px: the render prints `LOW-RES picture` for those, so replace them. Every circle/arrow/X must land on something meaningful: draw each point on the picture and look before rendering.
- `package.json`: title (the hook, lowercase, 1–2 hashtags, no answer), description with sources, `first_comment`.
- **Never** commit `.cache/`, `out/` or any downloaded media (public repo); only URLs.

## 4. Voice (Gemini only runs on Actions)
Freeze the script, then push the branch. `voice.yml` voices only episodes whose `episode.json` changed (one Gemini request; free tier is about 10 a day). Wait for the run (background until-loop, no foreground sleep), download the `voice` artifact with the GitHub MCP tools, put the raw take in `.cache/tts/`, and run `python3 buhexplains/pipeline/voice.py <slug>` locally (no API call). Changing `lines` text later costs another request; picture-only edits should be committed with `[skip ci]`. On a daily-quota error: commit the script, say so, stop.

## 5. Render and check
`buhexplains/make.sh <slug> --preview` while iterating, then `buhexplains/make.sh <slug>`. Look at a contact sheet and at frames where stickers fire. Run `python3 buhexplains/pipeline/audit.py <slug>` and fix real failures: hook asked after 3 s, holds over 2.5 s, frozen frames, loudness outside −11..−8 LUFS, voice under 85 % (misses on names and spelled numbers are Whisper, not a defect), wrong labels.

## 6. Ship
- `git fetch origin main && git rebase origin/main && git push origin HEAD:main` (fast-forward only, retry on a race, never force-push).
- In the same push, add the slug to `buhexplains/queue.txt` (time-critical near the top, evergreen at the end with `# buffer (evergreen)`).
- Dispatch `render.yml` on ref `main` with the slug (GitHub MCP `actions_run_trigger`). The uploader uses the newest successful `film-<slug>`.
- Add the MP4 to the `videos` branch from a separate worktree (`git worktree add ../buh-videos origin/videos` if missing; copy, commit, push).

## 7. Report
Five lines: the episode, its hook, its reveal, its sources, the audit results. Send the MP4 to the user if they're around.

Never upload to YouTube by hand (the cron does it from the queue), no PRs, don't change environment, permission, cron or scheduled-task settings.
