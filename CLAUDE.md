# buh-explains

Automation for **@BuhExplains**: 20–35 s meme-lore explainer Shorts (a TTS narrator, real pictures edited over the top, built for hook / build-up / payoff). HelloBuh lives in its own repo now (`evanlin23/hello-buh`); `hellobuh/` here is the old trial pointer only.

## Read first
- `buhexplains/PLAYBOOK.md`: how ideas are picked, scripts written, pictures, sound and voice made, and videos judged. **Owner notes outrank everything except accuracy.** When the owner gives feedback, add it to the playbook as a dated quote, in the same commit.
- `buhexplains/reference/TUNG_BREAKDOWN.md`: the hit, measured frame by frame (shake, pacing, loudness, sound bite).

## Layout
- `buhexplains/episodes/<slug>/`: `episode.json` (lines, beats, pictures with `points`, name bites, music, sources), `script.md`, `package.json` (title, description, first comment), `manifest.json` (written by the render: every picture/sound source).
- `buhexplains/pipeline/`: `fetch_assets.py` (rebuild `.cache/` from logged URLs), `voice.py` (Gemini Achird or Kokoro; the narrator says the names, `voice.bites: false`), `render.py` (picture + sound + mix), `voicecheck.py` (clipped cuts + intelligibility in the final mix), `shake_measure.py`, `bite.py`, `upload.py`, `comment.py`, `audit.py` (virality QA on the finished file).
- `buhexplains/assets/sfx/`: the owner's own sound kit (committed). `buhexplains/assets/sfx_sources.txt`: the myinstants kit's URLs.

## Skills (`.claude/skills/`)
- `/buh-episode`: make one episode end to end (the producer runs this twice a day).
- `/buh-scout`: find live memes and write scored pitches.
- `/buh-rerender`: push a pipeline fix to every not-yet-uploaded episode and refresh the `videos` branch.
- `/buh-status`: are uploads, comments, production and the buffer healthy; what's going up today.

## Commands
```bash
buhexplains/make.sh <slug>             # fetch_assets -> voice -> render -> voicecheck
buhexplains/make.sh <slug> --preview   # half-size render, no voicecheck
```

## Voice (Gemini) runs on Actions
`GEMINI_API_KEY` is a repo secret that only Actions can read. Pushing a change to an episode script or `voice.py` runs `.github/workflows/voice.yml`: one Gemini request per changed script (free tier is about 10 a day; keep the script final before pushing), cached by text. Its artifact `voice` carries each episode's `voice.wav`, `words.json` and **Gemini's raw take** (`.cache/tts/*.wav`). Put the raw takes in `.cache/tts/` and `voice.py` runs locally with no API call, so splices and cleanup can be tuned for free.

## Media policy
`.cache/` (models, stock clips, myinstants sounds, music, bites, pictures, raw TTS) is never committed: the repo is public and these are other people's files. Every one has its URL logged (`episode.json`, `sfx_sources.txt`, `render.STOCK`), and `fetch_assets.py <slug>` rebuilds it. Renders (`out/`) aren't committed either.

## Operations
`docs/operations.md`: the daily schedule (2 uploads and 2 productions a day), the producer session and its scheduled tasks, the cron-job.org jobs, secrets and variables, how to pause or reorder, and the known failure modes. Read it before changing any of them.

## Uploads
**Live since 2026-11-06.** `render.yml` makes the `film-<slug>` artifact; `upload.yml` posts 2 a day from `buhexplains/queue.txt` (private, scheduled public about noon and 6 PM Central); `comments.yml` posts each video's first comment once it's public. Turn everything off by removing the repo variable `YT_ENABLED`. Details: `docs/operations.md`.

## Commit identity
```bash
git config user.name evanlin23
git config user.email 113861384+evanlin23@users.noreply.github.com
```
**`main` is what runs** (owner, 2026-11-07: "just get everything to main"). The daily upload clock (cron-job.org → `upload.yml`, ref `main`) runs main's code, uploads main's `queue.txt`, and commits `uploads.json` there. Work on a branch, and once it's tested, merge it to `main` (fast-forward or merge commit). No PR unless asked.
