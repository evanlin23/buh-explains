# buh-explains

Automation for two of the owner's YouTube channels:

- **@BuhExplains** (`buhexplains/`, built in this repo's main session): short meme/lore explainers. Style research: `evanlin23/content` → `research_notes/buhexplains_editing_style.md`.
- **@HelloBuh** (`hellobuh/`, built by a separate session): captioned Minecraft stunt Shorts, played and recorded by a bot. See `hellobuh/README.md`.

Shared house rules, inherited from `evanlin23/blocky-stories` and `evanlin23/content`:
- Budget $0: free tools only. Renders and uploads run on GitHub Actions. cron-job.org is the clock, because GitHub `schedule:` never fires for this owner.
- Uploads go up private with a scheduled publish, using the owner's own OAuth (copy `blocky-stories/docs/youtube-setup.md` and `scripts/upload.py`).
- Each channel keeps one lane. No video goes on two channels. Every video needs its own angle, because YouTube reviews "templated" content channel-wide.
- Times for the owner are in US Central.

## Commit identity
```bash
git config user.name evanlin23
git config user.email 113861384+evanlin23@users.noreply.github.com
```
