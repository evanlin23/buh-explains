# Tung (the hit), measured from the original file

Source: the owner's upload of `--iwNivqlo4`, 2026-11-06 (720×1280, 30 fps, 28.98 s, AAC 44.1 kHz stereo). The file is kept out of git (`*.mp4`). Measured with ffmpeg ebur128, librosa and faster-whisper `small.en`, plus 4 fps contact sheets read frame by frame. Word timings: `tung_words.json`.

## Sound
| Measure | Value | What it means for us |
|---|---|---|
| Loudness | **−8.0 LUFS integrated**, LRA **1.6 LU** | Very loud and flat. Ours went out at −16. Match it: about −9 LUFS, heavily compressed. |
| Floor | the quietest 5% of the video sits at −15.5 dB RMS | There's never silence. A music bed runs under every word, gaps included. |
| Music | continuous, about **112 BPM**; Whisper found no lyrics over the voice | Instrumental, or lyrics buried under the voice. The owner adds the song at upload. |
| Cuts vs the beat | cut → nearest beat 0.100 s median (random: 0.137 s) | The edit does **not** follow the music |
| Cuts vs the voice | cut → nearest word onset **0.070 s** median | The edit follows the **voice**. Cutting on words is right; no beat grid needed. |
| Voice | median f0 120 Hz (p10 71, p90 258), a wide, expressive range | A low male narrator with a lot of lift. Direct Achird lower and livelier than flat. |
| Pace | 92 words recognised (about 100 counting every "tung"), **3.2–3.5 words/s**, 0.0 → 28.78 s | Speech from frame 0 to the last 0.2 s |
| Pauses | only 3 over 0.25 s (3.4 s, 21.2 s, 25.8 s) | No air. Pauses only before "You see" and before the payoff |
| Percussive hits | 21 onsets; clusters at 0–1.5 s, 16–19.6 s and 26–27.6 s | Booms and whooshes on the stingers, densest at the opening and the ending |

## The name is the meme's own sound bite (owner, 2026-11-06)
"When it says 'tung tung tung sahur' it uses the tung tung tung sahur sound byte." The narrator never says the name; the meme's original audio clip plays instead. Measured: mentions 2–4 (4.1, 10.9, 17.8 s) are one clip (MFCC similarity 0.56–0.80, against about 0.1 for the narration around them). Mentions 1 and 5 have the opening and ending SFX stacked on them. Each runs about 1.0 s. This is why the name's length never varied and Whisper heard it the same way every time.

## Picture
| Measure | Value |
|---|---|
| Hard picture changes | 21 (7.2 per 10 s), plus a sticker, label or overlay change about every 0.25–0.5 s on top |
| Near-still frames | **2.8%** (mean pixel change < 1.5). Something moves on 97% of frames. |
| Global motion | 45% of frames move ≥ 4 px (at 1080 wide) from the last frame; p95 is 42 px. The **whole frame shakes, captions included**. |
| Name stinger | Every "Tung tung tung tung sahur": a real fire-explosion ring fills the frame (4.0, 10.8, 17.7, 26.5 s), then the character **with real fire footage blended over it** (screen-style, flames licking the whole image), not a separate drawn band |

## The visual vocabulary (frame by frame)
- **Full-bleed pictures, always.** The meme's own render, 3D fan art on white, the Rome monument, a map of Italy, a "TUNG TUNG TUNG TUNG SAHUR" poster, a sahur meal photo, an Indonesia map, a sunset pier, a full-screen Indonesian flag. Nothing small on a dark background. One letterboxed shot (16–17 s): the image in a middle band, black above and below.
- **Red hand-drawn ellipse** (double stroke), and it **moves**: it sweeps around the face at 0.25–1.0 s, scribbles around the body at 8.75–9.25 s, and slides across the poster title at 12.5–14.25 s.
- **3D red arrow:** points at the subject from the bottom on frame 0, at the bat (9.25–9.75 s), and at Indonesia on the map (20.5–21.75 s), twice. It slides and bobs.
- **Glowing warning triangle:** pink-red neon outline with a yellow "!", **blinking** on and off about 4×/s over "isn't actually Italian".
- **Hearts:** pop on "love" and jump to a new spot every beat (5.5–7.0 s).
- **Waving flags:** a 3D waving flag sticker, with a red "!?" on "Italian brainrot".
- **A "3":** a 3D number on a dark tile that jumps to a new spot on each word ("three times does not answer", 15.75–17.5 s).
- **Lightning flashes:** blue-white electric overlays at 0.25–0.75 s and 26.75–27.0 s.
- **Pink-glow labels** ("TUNG = SOUND OF A DRUM", "SAHUR = meal eaten before dawn during Ramadan", "3:00 AM", "RAMADAN"): they **type on letter by letter** and leave by **scattering their letters**.
- **Transitions:** zoom blur (8.5 s), whip with motion blur (19.25 s), a mirror/kaleidoscope warp (15.75 s, 22.0 s), and the Indonesian flag **spinning in** at 28.25 s for the last word.
- **Small pink sparkles** drift over the sunset (24 s).
- **Captions:** 1–2 words, white, a clean bold sans with a soft drop shadow and no heavy outline, **small** (about 4% of the frame height), dead centre or just below. Smaller and lighter than our draft's.
- **Colour:** warm, saturated orange-red grade on the character shots.

## The script (as spoken)
> Did you know that tung tung tung tung sahur isn't actually Italian? You see, the tung tung tung tung sahur we all know and love is the iconic Italian brainrot woodman carrying a bat. But the origin of tung tung tung tung sahur lies in its name. It is said that if someone is called for sahur three times and does not answer, then tung tung tung tung sahur will come to their house. You see, in Indonesia, sahur is the meal consumed by Muslims before dawn during the month of Ramadan. This makes tung tung tung tung sahur actually Indonesian.

The answer ("Indonesian") is the last word, at 28.0 s. "Indonesia" is first said at 20.6 s (71%), and the map with the arrow arrives with it. The name is said 5 times, each with a stinger. This is the exact shape PLAYBOOK §3 now requires.
