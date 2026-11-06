"""Writes ops.json so the bot (offline-mode name) is op on the local server."""
import hashlib, json, sys, uuid
name, out = sys.argv[1], sys.argv[2]
h = bytearray(hashlib.md5(f"OfflinePlayer:{name}".encode()).digest())
h[6] = (h[6] & 0x0F) | 0x30; h[8] = (h[8] & 0x3F) | 0x80
json.dump([{"uuid": str(uuid.UUID(bytes=bytes(h))), "name": name, "level": 4, "bypassesPlayerLimit": False}], open(out, "w"), indent=2)
