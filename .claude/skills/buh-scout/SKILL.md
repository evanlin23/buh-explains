---
name: buh-scout
description: Find live memes for @BuhExplains and write scored pitches to buhexplains/pitches/<date>.md. Use when asked to scout, find trends or topics, refill the buffer, or as step 1 of /buh-episode.
---

# Scout memes for BuhExplains

1. Read `buhexplains/PLAYBOOK.md` (owner notes are binding; §2 is the scoring table, §4 the story shapes) and the last 3 files in `buhexplains/pitches/`.
2. Candidates: memes live in the last ~2 weeks. Web search (Know Your Meme new entries, news "viral meme", TikTok/Shorts trend roundups) plus demand checks: `yt-dlp --flat-playlist "ytsearch20:<meme>"` view counts, Shorts 1M+.
3. Skip anything already in `buhexplains/episodes/` or rejected in `buhexplains/pitches/`. Old memes ("6-7") fail the "live right now" gate unless the pitch is explicitly an evergreen buffer.
4. Score each with PLAYBOOK §2 (gates, then gap × comment engine). Note the story shape and that it differs from the last 2 episodes (`ls buhexplains/episodes`).
5. Safety: politics OK with no party side; nothing sexual, about minors, targeting private people, or exploiting tragedies.
6. Each pitch: hook (≤ 10 words, a question, answer NOT in it), the reveal (lands after 70%), two sources (one primary), demand evidence, time-critical or evergreen. Append to `buhexplains/pitches/<YYYY-MM-DD>.md` (add a letter suffix if the file exists) and commit it.
