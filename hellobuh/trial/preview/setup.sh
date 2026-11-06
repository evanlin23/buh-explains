#!/usr/bin/env bash
# prismarine-viewer fallback renderer (no Minecraft account needed). Installs pinned deps into
# work/pv and applies two local patches:
#  1. viewer worker skipped every block face below y=0 (pre-1.18 assumption) -> blank world
#  2. mineflayer 4.26 sends use_item with rotation (0,0), so the server raycasts the bucket
#     horizontally (4.39 sends the real rotation; 4.26 is needed because the viewer's prebuilt
#     browser bundle only understands early-2025 chunk formats, i.e. MC <= 1.21.4)
set -euo pipefail
cd "$(dirname "$0")/.."
mkdir -p work/pv && cp preview/package.json preview/capture.js work/pv/
(cd work/pv && npm install --no-audit --no-fund)
W=work/pv/node_modules/prismarine-viewer/public/worker.js
sed -i 's/if(g\.position\.y<0)continue;/if(g.position.y<-64)continue;/; s/if(n\.position\.y<0)continue}/if(n.position.y<-64)continue}/' "$W"
I=work/pv/node_modules/mineflayer/lib/plugins/inventory.js
sed -i "s|rotation: { x: 0, y: 0 }|rotation: { x: require('../conversions').toNotchianYaw(bot.entity.yaw), y: require('../conversions').toNotchianPitch(bot.entity.pitch) }|" "$I"
grep -q "position.y<-64" "$W" && grep -q toNotchianYaw "$I" && echo "preview renderer ready"
