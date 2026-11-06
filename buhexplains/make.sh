#!/usr/bin/env bash
# One episode, end to end, in this checkout:  buhexplains/make.sh <slug> [--preview]
# fetch_assets -> voice (local when Gemini's raw take is cached in .cache/tts; otherwise it needs GEMINI_API_KEY,
# which only Actions has: push the episode and let .github/workflows/voice.yml make it) -> render -> voicecheck.
set -euo pipefail
cd "$(dirname "$0")/.."
slug="${1:?usage: buhexplains/make.sh <slug> [--preview]}"; shift || true
python3 buhexplains/pipeline/fetch_assets.py "$slug"
python3 buhexplains/pipeline/voice.py "$slug"
python3 buhexplains/pipeline/render.py "$slug" "$@"
if [ "${1:-}" != "--preview" ]; then python3 buhexplains/pipeline/voicecheck.py "$slug"; fi
