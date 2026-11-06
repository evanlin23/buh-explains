"""Download the Minecraft Java client (+ Fabric loader, ReplayMod) from Mojang / Fabric / Modrinth.

No third-party launcher: reads Mojang's version manifest and Fabric's profile JSON, fetches the
client jar, libraries and assets (sha1-checked), and writes work/client/launch.json with the
classpath and arguments that launch.py needs. Idempotent; safe to cache on CI (work/client).

usage: python3 fetch_client.py
"""
import concurrent.futures as cf
import hashlib
import json
import os
import pathlib
import sys
import urllib.request

HERE = pathlib.Path(__file__).resolve().parent
ENV = dict(l.split("=", 1) for l in (HERE / "versions.env").read_text().splitlines() if "=" in l and not l.startswith("#"))
MC, LOADER = ENV["MC_VERSION"], ENV["FABRIC_LOADER"]
ROOT = HERE / "work" / "client"
LIB, ASSETS = ROOT / "libraries", ROOT / "assets"


def fetch(url, dest, sha1=None):
    dest = pathlib.Path(dest)
    if dest.exists() and (sha1 is None or hashlib.sha1(dest.read_bytes()).hexdigest() == sha1):
        return dest
    dest.parent.mkdir(parents=True, exist_ok=True)
    for attempt in range(4):
        try:
            with urllib.request.urlopen(url, timeout=60) as r:
                data = r.read()
            break
        except Exception:
            if attempt == 3:
                raise
    if sha1 and hashlib.sha1(data).hexdigest() != sha1:
        raise RuntimeError(f"sha1 mismatch for {url}")
    tmp = dest.with_suffix(dest.suffix + ".part")
    tmp.write_bytes(data)
    tmp.replace(dest)
    return dest


def getjson(url):
    with urllib.request.urlopen(url, timeout=60) as r:
        return json.load(r)


def allowed(rules):
    if not rules:
        return True
    ok = False
    for r in rules:
        osn = r.get("os", {}).get("name")
        if "features" in r:
            continue
        if osn in (None, "linux"):
            ok = r["action"] == "allow"
    return ok


def maven_path(name):
    parts = name.split(":")
    g, a, v = parts[0], parts[1], parts[2]
    cls = f"-{parts[3]}" if len(parts) > 3 else ""
    return f"{g.replace('.', '/')}/{a}/{v}/{a}-{v}{cls}.jar"


def main():
    manifest = getjson("https://piston-meta.mojang.com/mc/game/version_manifest_v2.json")
    entry = next(v for v in manifest["versions"] if v["id"] == MC)
    vj = json.loads(fetch(entry["url"], ROOT / "versions" / f"{MC}.json", entry["sha1"]).read_text())
    fab = getjson(f"https://meta.fabricmc.net/v2/versions/loader/{MC}/{LOADER}/profile/json")

    jobs = [(vj["downloads"]["client"]["url"], ROOT / "versions" / f"{MC}.jar", vj["downloads"]["client"]["sha1"])]
    cp = []
    seen = set()
    # Fabric libraries first (they win on conflicts, e.g. ASM), then vanilla.
    for lib in fab["libraries"]:
        p = maven_path(lib["name"])
        key = ":".join(lib["name"].split(":")[:2])
        seen.add(key)
        jobs.append((lib["url"].rstrip("/") + "/" + p, LIB / p, lib.get("sha1")))
        cp.append(LIB / p)
    for lib in vj["libraries"]:
        if not allowed(lib.get("rules")):
            continue
        art = lib.get("downloads", {}).get("artifact")
        if not art:
            continue
        key = ":".join(lib["name"].split(":")[:2]) + (":" + lib["name"].split(":")[3] if lib["name"].count(":") > 2 else "")
        if key in seen:
            continue
        jobs.append((art["url"], LIB / art["path"], art["sha1"]))
        cp.append(LIB / art["path"])
    cp.append(ROOT / "versions" / f"{MC}.jar")

    ai = vj["assetIndex"]
    idx = json.loads(fetch(ai["url"], ASSETS / "indexes" / f"{ai['id']}.json", ai["sha1"]).read_text())
    for obj in idx["objects"].values():
        h = obj["hash"]
        jobs.append((f"https://resources.download.minecraft.net/{h[:2]}/{h}", ASSETS / "objects" / h[:2] / h, h))

    mods = ROOT / "mods"
    for k, name in [("FABRIC_API", "fabric-api.jar"), ("REPLAYMOD", "replaymod.jar")]:
        jobs.append((ENV[f"{k}_URL"], mods / name, ENV[f"{k}_SHA1"]))

    print(f"{len(jobs)} files to check/download", flush=True)
    with cf.ThreadPoolExecutor(16) as ex:
        for i, _ in enumerate(ex.map(lambda j: fetch(*j), jobs)):
            if i % 1000 == 0:
                print(f"  {i}/{len(jobs)}", flush=True)

    launch = {
        "mainClass": fab["mainClass"],
        "classpath": [str(p) for p in cp],
        "assetIndex": ai["id"],
        "jvm": [a for a in fab.get("arguments", {}).get("jvm", []) if isinstance(a, str)],
        "javaMajor": vj.get("javaVersion", {}).get("majorVersion"),
    }
    (ROOT / "launch.json").write_text(json.dumps(launch, indent=1))
    print("ok", ROOT / "launch.json", "java", launch["javaMajor"])


if __name__ == "__main__":
    sys.exit(main())
