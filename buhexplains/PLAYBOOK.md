# BuhExplains playbook

How a BuhExplains Short gets picked, written, cut and judged. Every rule here comes from something we've measured or something the owner said. **[M]** = measured (our channels, or data scraped from others), **[B]** = belief (a hypothesis, house research or a panel). Sources are in `evanlin23/content`, `blocky-stories`, `sixdegrees`, `data-driven` and `niche`. The citations are at the bottom.

The owner's words outrank everything here except accuracy. Add new owner feedback to "Owner notes" as a dated quote, in the same PR.

## Owner notes
- 2026-11-06: "Can we do 2x per day?" / "can we post 2x per day as well?" A daily producer session makes a video at 1:23 PM and 8:41 PM Central. Uploads: 2 a day from `queue.txt`, public about noon and about 6 PM Central.
- 2026-11-07: "why is the quality of the video uploaded so bad?" (ep06). The uploaded file was full 1080x1920 at 8 Mbps; the softness was ours: 69 of 114 pictures were under 900 px wide, mostly 480x360 YouTube thumbnails (`hqdefault`, `hq1-3`) stretched to 1080 every frame. Now: YouTube stills are swapped automatically for `maxres`/`sd` of the same frame (41 of 47 were available); anything smaller than 1400 px is upscaled once with Lanczos and sharpened; per-frame resizes are bicubic; flames come from Mixkit's 1080p clips; the encode is CRF 15 `slow` (about 16 Mbps) so YouTube's re-encode has more to work with. Sourcing: **pick pictures at least 1000 px on the long side**; the render prints `LOW-RES picture` for anything under 600 px. ep06 stays as uploaded; everything after it is re-rendered.
- 2026-11-07: "The main goal is the virality (hook, build up, payoff)" and "it just needs to be able to go viral, not necessarily follow BuhExplains' old ones exactly". "My hook was like starting zoomed out and quickly zooming in." Every video now gets `render.viral_pass`:
  - **Hook:** the first shot starts at a third of its size on black and snaps to full size in 0.38 s, with a whoosh.
  - **Build-up:** no shot holds longer than about 1.2 s; long holds get jump cuts alternating a tight crop on the picture's point of interest with the full shot. A riser builds into the final line.
  - **Payoff:** the last word gets a punch, a white flash and an impact, then a cut 0.2 s later for the loop.
  - `pipeline/audit.py` checks all of this on the finished files: hook timing, changes per 10 s, longest hold, frozen and black frames, tail, loudness, true peak and voice.
- 2026-11-07: ep04's framing of Elizabeth Holmes (court-record facts only: convicted of defrauding investors, 11 years) is OK. On length: "we can experiment with lengths, that's fine". Vary length between about 20 s and 35 s across episodes, and let the metrics decide (log each video's length next to its numbers).
- 2026-11-07: "the name spliced in doesn't really work, can you do just the regular voice?" The narrator says the names itself (`voice.bites: false`). The fire and explosion still hit on every name; only the audio changed. The bite tools stay in the code in case a meme's sound is ever worth bringing back.
- 2026-11-06: TTS narration with Gemini **Achird**. This repo gets its own secrets; never reuse other repos' keys.
- 2026-11-06: "6 7 is old, we need to be more trendy and recent." Only memes that are live right now.
- 2026-11-06: "Why cant we be controversial or political." Controversy and politics are allowed here. This replaces the blocky channel's "nothing that would decrease the possible audience size" rule for BuhExplains only. House approach: the viewers argue, and the channel doesn't take a party side.
- Music: a viral song is added at upload, from YouTube's library. The export carries voice and SFX only, cut to the song's beat.

## 1. What we know works

1. **A claim viewers can check, about something they already know, beats everything else.** **[M]** Tung ("…isn't italian?") got 108K views against 9.8K and 2.2K for its siblings, and 3× the comment rate (1.0 against 0.3 per 1K views). The Six Degrees reference channel's two hits made 73% of its 45M views from one shape: something everyone under 25 knows × a gap that seems impossible. Our own Leonardo → Naruto got 10× its siblings.
2. **The first second decides the run.** **[M]** The feed tests a Short for 1 to 4 hours on its viewed-vs-swiped rate, then drops it. back-row: 82.6% viewed went viral; 61–65% died. A static opening kept 24% against 44% for one that opened on the hook with the visual already moving.
3. **The picture never sits still.** **[M]** Hits change the picture 16.5 times per 10 s, with a 0.25 s longest still. Our flops managed 8–10. The old BuhExplains edit already did this: a new picture every 2–3 words.
4. **No explaining after the hook.** **[M]** back-row lost 14 points at 4.1 s on a routine line. Its worst stretch was a character explaining the rule. Every line after the hook is new evidence.
5. **Loops pay.** **[M]** back-row's curve starts at 166% and its last 6 s were its strongest. The 19.9M-view sonified Short runs 25 s with no outro. Tung's last word ended the video.
6. **Short, or long. Never the middle.** **[M]** Gags of 13–45 s and stories of 100–175 s win; 0 of 28 Shorts at 46–75 s made the top 10%. Old BuhExplains ran 19–32 s.
7. **Hits drive everything.** **[M]** The top 3 videos take 58–91% of a channel's views, and the median video gets 5–30% of the mean. So judge the format over a run, not one upload: no video past 10K after 30 uploads means the format is wrong, not the cadence.
8. **Comments come from claims people can confirm or correct.** **[M]** Tung's top comment was agreement ("Finally someone who explains it is NOT ITALIAN"). Corrections ("sahur isn't only Indonesian") added volume. The creator wrote 25 of its 98 comments. A premise that makes viewers type something specific got 0.74% comments per view, against a 0.01% median.
9. **Narrow topics die. Copycats die.** **[M]** A pandemics copycat of the sonified breakout got 0.16% of its views. Team-specific, local or time-bound topics got 0.0–0.1× the channel median.

## 2. Picking an idea

Score every candidate before writing a word. One that fails a **gate** is out.

| Test | Gate or score | How to check |
|---|---|---|
| **Live right now** | gate | Most activity is in the last ~6 weeks: a KYM guide, news coverage, or Shorts climbing this month. "6-7" fails. |
| **Recognised on sight** | gate | Shorts about it have 1M+ views, *or* other creators' comment sections name it unprompted (Verity: top comments with 2.4–2.7K likes on 9–11M-view Shorts). |
| **The gap** | score 1–5 | How far the truth is from what most viewers assume. "Isn't Italian", "is from Minecraft", "is 12 years old" all land. "Was made by a TikToker" doesn't. |
| **Said in ≤ 10 words** | gate | The hook *is* the title. If the claim needs a clause to make sense, it's the wrong claim. |
| **Checkable** | gate | Two independent sources, one of them primary (the original upload, post or song). No unsourced lore (we never found a source for Tralalero's "snail cat"). |
| **Comment engine** | score 1–5 | Will viewers confirm it, correct it, or type something (their favourite variant, where they first saw it)? |
| **Seen in a normal week** | gate | Note 12, rewritten for memes: the viewer has met this meme in their own feed. A meme only stats fans know fails. |
| **Story shape** | gate | Not the same shape as either of the last two videos (§4). |
| **Safe** | gate | No slurs, nothing sexual, no harassment of a real private person, no election misinformation. Politics is fine (owner, 2026-11-06). A hot-button topic means limited ads: decide on purpose. |

Then rank by gap × comment engine. Trend content ships fast: YouTube's own guidance is to post trends as soon as possible.

## 3. The script

**Length:** 20–30 s, 75–110 words. Achird at about 3.8 words/s (the old videos ran about 3.3, narrated hits about 4.4). Never past 45 s.

**Retention comes first: the hook opens a question, and the answer is held for the end.** **[M]** All three old videos open on a question and answer it in the last 15–20%: Tung at 26.2 s of 29 ("This makes it Indonesian"), Tralalero at 14.9 s of 19, Bombardiro at 27.5 s of 32. The hit's hook says what the meme *isn't*, so "then where?" carries the viewer to the end.
- **The title and hook never contain the answer.** Use the negative ("isn't X"), the question ("what did it originally look like?") or the wrong belief, never the reveal itself. "Do you know Verity is from Minecraft?" fails; "Do you know Verity isn't from The Amazing Digital Circus?" passes.
- **The middle rules out wrong answers.** Each beat closes a small question and opens a smaller one: "It looks like Caine. It isn't Caine." "It's not from the movie either." The viewer's guesses get knocked down one at a time, and the real answer gets closer without being said.
- **Re-hook at about 10–14 s** with a turn ("Until it isn't.", "But that's not the weird part.") so there's no flat middle.
- **The gate:** the main answer's first word lands after 70% of the runtime, and no line before it says or shows the answer, including stickers, labels and B-roll. A Minecraft grass block on screen at 3 s gives it away just like the word would.

**The beats** (the house formula that won, plus what back-row taught):

| Time | Beat | Rules |
|---|---|---|
| 0.0–2.5 s | **Hook** | A question, or "isn't…", read aloud from frame 0. ≤ 10 words. **No answer.** Frame 1 is the meme itself, big and already moving. Never "What if", never fake suspense ("you won't believe"). |
| 2.5–6 s | **The belief** | One line naming what everyone thinks: "You see, the X we all know and love is…". The audience already quoted this line back as our signature. It carries 2–3 picture changes. One line only, never two. |
| 6–19 s | **Wrong answers and clues** | 2–4 concrete beats: knock down the obvious guesses, and give real clues (a name, a date, a number) that point *toward* the answer without naming it. A re-hook turn at about 10–14 s. Each beat gets its own picture. Join them with "but" and "so", never "and then". |
| after 70% | **The reveal** | "But…" plus a fireball, a hard cut and a sound hit, then the answer, said plainly in one line over one big picture. A short pause just before it is the only real pause in the video. |
| last 2 s | **Payoff** | "This makes X…", the answer as a verdict and the last word, worded so it runs back into the hook on the loop. A 0.2–0.3 s tail, then the cut. |

**Always:**
- **The name is the meme's own sound bite**, not the narrator (owner, 2026-11-06; measured on Tung). Every time the name comes up, the meme's signature clip (about 1 s) plays under the fireball stinger. The script marks it `{name}` and the TTS skips it. Every bite is logged in the manifest with its source. **Copyright risk:** a clip from a commercially released song can draw a Content ID claim, even for 1 s. A claimed Short stays up, but its ad money goes to the rights holder. A bite from an original TikTok or an AI voice meme is lower risk. Decide per meme.
- The meme's name is said 3–5 times, with the fireball stinger every time. The repetition is the rhythm.
- Mock-serious register: deadpan documentary seriousness about absurd lore, plus one real-world fact. The register clash is the joke.
- A pause only right before the reveal. Elsewhere, no gaps.

**Never:**
- No CTA, no "subscribe", no "follow for part 2", no moral, no recap.
- Note 9's AI tells: em dashes, semicolons, "not just X but Y", rule-of-three slogans, delve/journey/fascinating, "ever wondered". Contractions are fine. Numbers, not adjectives.
- Nothing invented. If a link isn't sourced, it isn't in the video. Viewers call a fudged link "a cheat".

## 4. Story shapes (rotate; never the same as the last two)
YouTube's own first example of mass-produced content is "templated storylines". A "Do you know X? … here's the original" series is that template, so the *shape* changes even when the voice and edit stay the same.
- **Origin:** "it isn't from where you think" (Tung, Verity). The place is the reveal.
- **Age / timeline:** "it's way older than you think" (The Last Dance).
- **Hoax / nothing:** "it's counting down to nothing" (the November polar bear).
- **Mistranslation:** "it doesn't mean what you think".
- **Power scaling:** "how strong is X, really?", using real-world specs (Bombardiro and the B-25).
- **Hidden link:** "X and Y are connected" (the Six Degrees shape).
- **Myth bust:** "everyone says X; the source says Y".
The hook wording varies too: "Do you know…", "X isn't…", "X is older than…", "Nobody tells you…". Titles alternate between question and claim, and we measure which wins (blocky data had 0 question titles in its top 10%; our only BuhExplains hit was a question).

## 5. Voice (Gemini TTS, Achird)
- **It runs on GitHub Actions** (`.github/workflows/voice.yml`), because `GEMINI_API_KEY` is a repo secret only Actions can read (owner, 2026-11-06: "I only added to the repo"). The job runs on any push that changes an episode script or the voice code, and makes the artifact `voice` (voice.wav, words.json, joins.json per episode). The render step uses it.
- **The whole script goes in one request**, cached by text, then is cut into lines at the quietest point between them, by word timing. The free tier allows about 10 requests a day per model, and one take keeps the delivery consistent.
- **Never clip a word** (owner, 2026-11-06: "make sure the voice doesn't get cut off"). Trims keep 40 ms before and 70 ms after the speech, and only gaps over 0.2 s get squeezed (to 0.1 s). Splices snap to the quietest instant near the word boundary, never inside the previous word, with 6 ms crossfades. `pipeline/voicecheck.py` reports any cut made while the voice was still sounding, and how much of the narration Whisper understands in the finished mix.
- **Bite transitions are smooth** (owner, 2026-11-06: "the transitions to and from the Verity sound bites are rough"). Each bite is EQ'd toward the narrator's average tone (at most ±8 dB), set to the loudness of the narration in the half second around it, and joined with 25 ms equal-power crossfades. Each fade-out starts *after* the cut point, over the start of the name being replaced, so the narrator's last sound before the bite survives ("makes"). Splice points are found on an envelope that counts hiss, because an "s" is quiet in plain loudness but still a sound. Voice tweaks run locally from Gemini's cached raw take (in the Actions artifact), so they cost no API requests. One cleanup chain then runs over the whole voice track, bites included: low cut, de-esser, 3:1 compression and a presence lift, so it sounds like one channel.
- **The voice sits on top:** a presence lift (+3.5 dB at 3 kHz, −2 dB at 250 Hz), music 8 LU and effects 7 LU under the voice, and the music dips 3 dB whenever the narrator talks.
- Use Google's layout: AUDIO PROFILE + DIRECTOR'S NOTES, then `## TRANSCRIPT`. A loose instruction line gets read aloud.
- Direction: "a dead-serious lore documentary narrator who knows this is absurd; quick, confident, a real lift on the turn and the reveal".
- One request per script, then split by Whisper word timings. Fail the build if any line's words aren't heard (Gemini sometimes skips lines) or if words are added. Trim the tail noise burst it sometimes adds.
- Check meme names by ear (Verity, ThatMob, Skunx, botsu). Free tier: about 10 requests a day, so cache.
- Don't fake "um"s; punctuation does the pacing. **Write years as they're said** ("twenty twenty-six"): Gemini reads "2026" as "two thousand twenty six". Labels keep the digits.

## 6. Picture and sound (the edit)
**The visual identity is real pictures pulled from online, edited over the top** (owner, 2026-11-06). Seen in the old frames (`content/research_notes/buhexplains_frames/`):
- **Full-bleed photos and renders** fill the 9:16 frame: the meme's own character art, fan art, merch photos, landmarks, maps, food, a full-screen flag. They are not small drawings on a dark background (draft 1 of ep01 got this wrong).
- The character sits over a **photographic fire/smoke plate** (real-looking flames filling the frame), or is letterboxed in a middle band with fire above and below.
- Red **hand-drawn ellipse** and **3D red arrow** pointing at the named detail; a warning sign, a heart and flags as stickers.
- Pink-glow labels for numbers and definitions ("TUNG = SOUND OF A DRUM", "3:00 AM").
- **Something always moves, and the whole screen shakes, captions included** (owner, 2026-11-06: "we had like something moving on screen at all times, and the entire screen was shaking. also like red circles moving around and hearts etc"). Measured on Tung: only 2.8% of frames are near-still; 45% of frames move ≥ 4 px.
- **The shake is continuous, fast and motion-blurred** (owner, 2026-11-06: "the shake is like continuous"; the frames show smeared, doubled outlines and small zoom pulses). There's a new offset every frame (about 8 px, 16 px on hits), blurred along its path, mostly sideways, with no rotation. **It moves the picture and stickers, not the captions**: Tung's captions stay put and only pop in size per word. Draft 3's snap-and-hold shaker misread the measurement: the "still" frames were frames the blur hid from it.
- **Flames look like CapCut's flame overlays** (owner, 2026-11-06). `flame_frames()` builds them from real flames shot on black (Mixkit 3765, 22834 and 3465): a flame wall rising from the bottom, a shorter one hanging from the top, tongues up both sides, drifting embers and a warm glow from below, screen-blended over the picture with the middle left clear for the subject. They're used on the hero shots and on every name mention.
- **Every circle, arrow and X points at something that matters** (owner, 2026-11-06: "the items on the screen need to actually circle something meaningful or point at something meaningful"). Each picture in `episode.json` lists `points` (face, mouth, title, character...) in picture coordinates, and a sticker with `target` locks onto that spot wherever the picture is drawn: the circle goes around it, the arrow's tip touches it, the X lands on it. Check a sheet of sticker frames before every full render.
- **Show the whole subject, never a crop of it** (owner, 2026-11-06: "is the stuff too zoomed in?"; measured: wide pictures showed 22%, square ones 39%). Wide and square pictures go full width over a blurred copy of themselves (`blurfill`); only portrait pictures fill the frame. Push-in is at most 4%.
- **The name never gets a pause before it** (owner, 2026-11-06: "did you know [pause] verity"). The TTS speaks the whole line, then the spoken name is cut out and the bite is spliced into its slot, so the sentence flows into it. Voicing the pieces separately made each one end like a finished sentence.
- **Stickers are alive:** red circles draw on, then orbit and slide; hearts jump to a new spot every beat; the warning sign blinks about 4×/s; arrows bob; flags wave; labels type on and scatter off.
- **Sound effects come from myinstants** (owner, 2026-11-06): the classic meme kit (vine boom, fast whoosh, the Metal Gear alert, huh, bonk, the Discord ping, anime wow, the Minecraft explosion, a thunder strike, a glitch, a riser). Each file and its URL goes in the manifest. These are other people's uploads, so a claim is possible. If one gets claimed, swap that sound out.
- **A ton of sound effects** (owner, 2026-11-06: "theres a ton a ton of sound effects and over the top editing"). Every picture change, sticker, label, flash and name gets its own hit. ep01 draft 2 has 57 in 28 s.
- **Sound effects land on their hit, and are never cut short** (owner, 2026-11-06: "the sounds are not cut correctly"). Build-up sounds (whooshes, the riser, the explosion) are placed so their *peak* lands on the event; impacts start on their onset. Each one plays to its natural end. Draft 3 started everything at the event, so the explosion boomed 1.3 s late and 10 sounds were chopped off mid-tail.
- **Pacing: talk without stopping.** Tung speaks at 3.2 words/s with only 3 pauses over 0.25 s. The TTS's sentence-end silences are squeezed to 0.05 s, and lines run straight into each other. The only real pause is the beat before the reveal.
- **The mix: voice on top, music clearly there, effects under the voice** (owner, 2026-11-06: "the sounds are too loud", "need background music"). Measured integrated loudness per stem: music about 4–6 LU under the voice, effects about 6 LU under it (the hits still punch because they're short). Draft 4 had the effects 5.5 LU *over* the voice, which buried the music. `render.py` writes `stem_voice/sfx/music.wav`, so this can be checked every time.
- **The name bite is the meme's most recognizable line, found online** (owner, 2026-11-06). For Verity: single mentions use "Verity!" from ThatMob's movie greeting ("Hello, I'm Verity, your personal helper friend"). The meme line "Hey, it's me, it's Verity!" is sung ("Varity") and turns to mush when cut to one word, so it only plays whole, where the script names the song. **Never muffled** (owner, 2026-11-06: "it's like muffled"): the voice track runs at 48 kHz with a high-quality resampler (a 24 kHz track had cut the bite's top end). Bites get a presence boost, a high shelf and a touch of exciter. The music ducks 6 dB under every bite, and the name boom stays low so it doesn't cover the word. Test a bite cut alone before using it: Whisper must hear the name. Source and cut points live in `episode.json`.
- **Music: the latest viral phonk** (owner, 2026-11-06). ep01 uses Montagem Alquimia (on 2026's viral phonk lists, 108 BPM), a 15 s myinstants clip looped on bar lines, 5 LU under the voice. A copyrighted song baked into the file will likely draw a Content ID claim; that's the owner's accepted trade.
- **The owner's own sound kit** lives in `assets/sfx/` (committed): vine boom, woosh, ding, metal pipe, "get out", fairy dust, rizz, heavenly, the Among Us reveal, the Taco Bell bong, doot doot 6 7. These come before the myinstants downloads.
- **Rebuilding:** `.cache/` (models, stock, downloaded sounds, music, bites, pictures) never goes in git, because the repo is public. `pipeline/fetch_assets.py <slug>` rebuilds it from the logged URLs.
- **A music bed under everything:** Tung's is continuous, about 7 dB under the voice. By default we bake in a free-licence Mixkit track (`episode.json` → `music`). Set it to null to leave room for a trending song added at upload instead.
- **Loudness:** Tung is mastered at −8 LUFS with a 1.6 LU range: loud and flat. Ours targets about −9 LUFS.
- **Cut on the voice, not the music.** Tung's cuts land 0.07 s from a word onset, and no closer to the beat than chance.
- Full measurements: `reference/TUNG_BREAKDOWN.md`.
- The pictures are found per beat by search (YouTube thumbnails, Fandom wikis, image search), each logged with its source URL in the episode's manifest.
The full grammar is measured in `content/research_notes/buhexplains_editing_style.md`. In short:
- A new picture or sticker every 2–3 words, ≥ 15 visible changes per 10 s, no still frame over 0.5 s. Captions don't count as motion.
- Fireball stinger + fire plate on every name mention. Constant shake, punch-ins and white flashes, never calm (owner).
- One- or two-word centre captions taken from the script, so names are spelled right. A caption appears exactly on its own first word. Pink-glow labels carry numbers and definitions.
- Keep clear of the feed UI: the top ~140 px, the right ~140 px below mid-height, and the bottom ~470 px.
- No near-black frames mid-video (they look like the end).
- Third-party images (meme art, screenshots) illustrate a spoken point for ≤ 2 s each. Narration covers ≥ 90% of the runtime. Every image goes in a manifest with its source. Flags, stickers and plates are made in-house.
- Audio: voice + synthesized SFX (boom on the stinger, whoosh on whips, pop on stickers), cut to the chosen song's beat grid. **No meme audio and no song in the export.** The owner adds the trending song at upload.

## 7. Packaging
- **Title** = the hook, lowercase-casual, plus at most 3 hashtags. **It never contains the answer.** Note 9 applies.
- **Cover** = a mid-video frame where the meme is big. One subject, 0–3 words.
- **Description**: two plain first-person lines, then sources.
- **First comment** (posted by the channel; the API can't pin): a question that makes people type something specific, e.g. "where did you first see verity?". Reply to comments in the first hour.
- **Audience:** Made for kids = **No** on every upload. Brainrot draws kids, and kids-mode deletes comments, which are this format's engine. The register stays teen/adult.

## 8. Judging a video (from YouTube Studio / the Analytics API)
| Metric | Bar | Why |
|---|---|---|
| Viewed vs swiped | ≥ 70% strong, < 60% the hook failed | The feed's first test |
| Average viewed | ≥ 100% | Loops are working |
| Comments per 1K views | ≥ 1.0 | Tung's rate |
| Views at 72 h | log it | Hits drive everything |
After every 10 uploads, write what was measured into `buhexplains/LEARNINGS.md`, and retire rules that the numbers contradict.

## Sources
- `content/research_notes/buhexplains_editing_style.md`: 22-30 (stats), 66-107 (formula, pacing), 199-205, 310-336 (policy)
- `blocky-stories/docs/research/`: `playbook.md`:12-42, `craft-metrics.md`:165-188 and 232-234 and 283-286, `2026-11-03-our-retention.md`:72-99, `2026-11-03-market-analysis.md`:17-108, `2026-11-09-week.md`:14-33 and 166-173, `2026-11-02-creepy-lane-notes.md`:108-159
- `sixdegrees/docs/STYLE.md`:5-61, `.claude/skills/six-degrees-episode/SKILL.md`, `sixdeg/tts_gemini.py`:18-44, `sixdeg/audio.py`:294-321, `data/pairs.json`
- `data-driven/research/`: `packaging-playbook.md`:16-149, `human-feel-guide.md`:37-120, `cadence-growth.md`:11-200, `gap-analysis.md`:16-31
- `niche/docs/LESSONS.md`:66-81 and 245-290, `script-style-guide.md`:31-57
- `content/studio/style-guide.md` showrunner notes 9, 12, 13 and 17; `content/reports/Sonified history video playbook.md`:21-29 and 163

## Production notes (team, from ep04–05)
- **Dry-run before spending Gemini requests.** Put a stand-in narration in the TTS cache (Kokoro reading the exact script), run voice.py and a sticker-frame sheet, then delete the stand-in. Every beat word resolves and every target lands before the real take is requested.
- **Read voicecheck with care on number-heavy scripts.** Whisper writes "1994", "$60 million" and "1st", so spelled-out numbers show up as "misses" even when the voice says them perfectly (ep05: 85%, every miss a number). Look at the missed list, not just the percentage.
- **Watch long holds on one picture.** A teaser still, a tree or a banknote held for 4+ seconds reads as static. Add a close crop of the same picture (`cover` + `crop`), a related shot, or zoom punches on the stressed words.
- **Crop out other people's logos and titles** (A24 title cards, festival laurels) with `crop`, including on close-up variants.
