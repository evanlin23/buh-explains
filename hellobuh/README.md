# @HelloBuh: automated Minecraft stunt Shorts

> **Moved (2026-11-06):** HelloBuh now lives in its own repo, [`evanlin23/hello-buh`](https://github.com/evanlin23/hello-buh) (owner's call). That repo has the working pipeline, the trial report (`docs/trial.md`) and the format research. `hellobuh/trial/` here keeps the abandoned real-client/ReplayMod route for reference.

## The format (from the channel, 2026-11-06)
- 72 Shorts, 553 subscribers. Most get 20–40K views; the best is "re:zero instant respawn" (`PdcbpRxYKlc`) at 191K.
- First-person Minecraft **Java** survival footage, HUD visible (hotbar, hearts).
- A black band at the top with a white bold caption: "I hate this **job** 😭" (one word red), "????", "afk firework save", "POV: you can't afford x-ray".
- Sometimes an in-world green subtitle ("oh wow that was very close") and a meme image cut-in (a cat in a helmet over fire).
- Titles: short and lowercase, plus the "(do not check the sound 💀💀)" / "stop commenting your battery %" bait.
- Most clips are **staged stunts**: water-bucket and firework saves, lava tricks, end-portal "job", villagers, x-ray (one caption admits creative mode + WorldEdit).
- Cover frames: `research/cover-frames.jpg` (rows: re:zero, two "job" videos, ????, afk firework save, can't afford x-ray).
- The audio couldn't be fetched (YouTube bot-blocks downloads from cloud sessions), so the "check the sound" gag is unknown.

## Owner decisions
- 2026-11-06: **"close match is fine"**. The HUD and game sound don't have to be pixel-exact; a drawn HUD overlay is acceptable.
- 2026-11-06 (relayed by the orchestrator session): **"audio is just the game audio + whatever random viral song"**. Export the real game sound (fall, splash, hurt…), mixed at about -18 LUFS so there's headroom. Never bake a viral or copyrighted song into the export: it gets a Content ID claim, and the upload API can't attach a YouTube library track. The song is a manual step at upload (open question for the owner).

## Plan (trial first)
Bot plays a scripted stunt on a private server → the stunt is recorded as a replay → the replay is rendered headless to video → edit (caption band, crop, SFX) → upload. Details: the trial brief in the PR / session handoff.
