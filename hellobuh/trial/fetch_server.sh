#!/usr/bin/env bash
# Downloads the Fabric server + server mods into work/server (idempotent, sha1-checked).
set -euo pipefail
cd "$(dirname "$0")"; source versions.env
S=work/server; mkdir -p "$S/mods"
get() { # url dest sha1
  [ -f "$2" ] && [ -z "${3:-}" ] && return 0
  if [ -f "$2" ] && echo "$3  $2" | sha1sum -c --quiet 2>/dev/null; then return 0; fi
  curl -fsSL --retry 3 -o "$2" "$1"
  [ -z "${3:-}" ] || echo "$3  $2" | sha1sum -c --quiet
}
get "https://meta.fabricmc.net/v2/versions/loader/$MC_VERSION/$FABRIC_LOADER/$FABRIC_INSTALLER/server/jar" "$S/fabric-server.jar"
get "$FABRIC_API_URL" "$S/mods/fabric-api.jar" "$FABRIC_API_SHA1"
get "$FABRIC_KOTLIN_URL" "$S/mods/fabric-language-kotlin.jar" "$FABRIC_KOTLIN_SHA1"
get "$SERVER_REPLAY_URL" "$S/mods/server-replay.jar" "$SERVER_REPLAY_SHA1"
echo "eula=true" > "$S/eula.txt"   # Accepting the Minecraft EULA (https://aka.ms/MinecraftEULA) on the owner's behalf for a private local server.
cp server.properties "$S/server.properties"
