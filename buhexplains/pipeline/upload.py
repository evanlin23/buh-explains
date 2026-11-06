"""Upload one rendered episode to @BuhExplains as a PRIVATE video with a scheduled publish, then open an issue.

    python buhexplains/pipeline/upload.py --slug ep01-verity [--dry-run]

Does NOTHING unless all of these exist: the secrets YT_CLIENT_ID, YT_CLIENT_SECRET, YT_REFRESH_TOKEN, the
variable YT_CHANNEL_ID, and the variable YT_ENABLED=true (docs/youtube-setup.md). It refuses if the token's
channel isn't YT_CHANNEL_ID, never uploads the same slug twice (uploads.json, and the channel's last 50 titles),
and sets Made for kids: No. Ported from evanlin23/blocky-stories scripts/upload.py.
"""
from __future__ import annotations

import argparse, datetime as dt, json, os, subprocess, sys, tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
EP = ROOT / "buhexplains" / "episodes"
UPLOADS = ROOT / "buhexplains" / "uploads.json"
REPO = os.environ.get("GITHUB_REPOSITORY", "evanlin23/buh-explains")
SLOTS_CENTRAL = [(16, 0), (19, 30)]   # first and second upload of a day go public at 4:00 and 7:30 PM Central


def enabled() -> tuple[bool, str]:
    need = ("YT_CLIENT_ID", "YT_CLIENT_SECRET", "YT_REFRESH_TOKEN", "YT_CHANNEL_ID")
    missing = [k for k in need if not os.environ.get(k, "").strip()]
    if os.environ.get("YT_ENABLED", "").strip().lower() != "true":
        missing.append("YT_ENABLED=true")
    return (not missing, ", ".join(missing))


def uploads() -> dict:
    return json.loads(UPLOADS.read_text()) if UPLOADS.exists() else {}


def publish_at(slot: int = 0) -> str | None:
    if os.environ.get("YT_AUTOPUBLISH", "true").strip().lower() == "false":
        return None
    import random
    from zoneinfo import ZoneInfo
    tz = ZoneInfo("America/Chicago"); now = dt.datetime.now(dt.timezone.utc).astimezone(tz)
    h, m = SLOTS_CENTRAL[min(slot, len(SLOTS_CENTRAL) - 1)]
    at = now.replace(hour=h, minute=m, second=0, microsecond=0) + dt.timedelta(minutes=random.randint(0, 12))
    if at < now + dt.timedelta(minutes=30):
        at = now + dt.timedelta(hours=1)
    return at.astimezone(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def film(slug: str, d: Path) -> Path:
    """Download the newest film-<slug> artifact from a successful render run."""
    runs = json.loads(subprocess.run(["gh", "run", "list", "--repo", REPO, "--workflow", "render.yml", "--status", "success",
                                      "--json", "databaseId", "--limit", "20"], capture_output=True, text=True, check=True).stdout)
    for r in runs:
        if subprocess.run(["gh", "run", "download", str(r["databaseId"]), "--repo", REPO, "-n", f"film-{slug}", "-D", str(d)]).returncode == 0:
            return next(d.rglob(f"{slug}.mp4"))
    sys.exit(f"no film-{slug} artifact: run the render workflow for {slug} first")


def youtube():
    from google.oauth2.credentials import Credentials
    from googleapiclient.discovery import build
    creds = Credentials(None, refresh_token=os.environ["YT_REFRESH_TOKEN"], client_id=os.environ["YT_CLIENT_ID"],
                        client_secret=os.environ["YT_CLIENT_SECRET"], token_uri="https://oauth2.googleapis.com/token")
    return build("youtube", "v3", credentials=creds, cache_discovery=False)


def main() -> None:
    ap = argparse.ArgumentParser(); ap.add_argument("--slug", required=True); ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()
    ok, missing = enabled()
    if not ok:
        print(f"uploads are off (missing: {missing}). Nothing done.")
        return
    pkg = json.loads((EP / a.slug / "package.json").read_text())
    done = uploads()
    if a.slug in done:
        print(f"{a.slug} is already uploaded ({done[a.slug].get('video_id')}). Nothing done."); return
    yt = youtube()
    me = [c["id"] for c in yt.channels().list(part="snippet,contentDetails", mine=True).execute().get("items", [])]
    if os.environ["YT_CHANNEL_ID"].strip() not in me:
        sys.exit(f"the token belongs to {me}, not YT_CHANNEL_ID; refusing to upload")
    pl = yt.channels().list(part="contentDetails", mine=True).execute()["items"][0]["contentDetails"]["relatedPlaylists"]["uploads"]
    titles = [i["snippet"]["title"].strip() for i in yt.playlistItems().list(part="snippet", playlistId=pl, maxResults=50).execute().get("items", [])]
    if pkg["title"].strip() in titles:
        sys.exit(f"a video titled {pkg['title']!r} is already on the channel; record it in uploads.json by hand")
    with tempfile.TemporaryDirectory() as td:
        mp4 = film(a.slug, Path(td))
        today = dt.datetime.now(dt.timezone.utc).date().isoformat()
        slot = sum(1 for e in done.values() if e.get("uploaded") == today)
        when = publish_at(slot)
        body = {"snippet": {"title": pkg["title"], "description": pkg["description"], "categoryId": "24"},
                "status": {"privacyStatus": "private", "selfDeclaredMadeForKids": False, "containsSyntheticMedia": False}}
        if when: body["status"]["publishAt"] = when
        print(f"{a.slug}: {pkg['title']!r}, {mp4.stat().st_size / 1e6:.0f} MB, publish at {when or 'never (private)'}")
        if a.dry_run: return
        from googleapiclient.http import MediaFileUpload
        req = yt.videos().insert(part="snippet,status", body=body,
                                 media_body=MediaFileUpload(str(mp4), mimetype="video/mp4", chunksize=16 << 20, resumable=True))
        resp = None
        while resp is None:
            st, resp = req.next_chunk()
            if st: print(f"uploaded {int(st.progress() * 100)}%", flush=True)
        vid = resp["id"]
    done[a.slug] = {"video_id": vid, "uploaded": today, "title": pkg["title"], "publish_at": when}
    UPLOADS.write_text(json.dumps(done, indent=1) + "\n")
    ref = os.environ.get("GITHUB_REF_NAME", "")
    subprocess.run(["git", "add", str(UPLOADS)], check=True)
    subprocess.run(["git", "commit", "-m", f"uploads: {a.slug}"], check=True)
    if ref: subprocess.run(["git", "push", "origin", f"HEAD:{ref}"], check=True)
    body = (f"**{a.slug}** is uploaded to @BuhExplains (private"
            + (f", goes public at {when} UTC on its own" if when else "") + f").\n\n"
            f"1. Watch it: https://studio.youtube.com/video/{vid}/edit\n"
            f"2. Add the trending song in YouTube's editor if this episode leaves room for one (episode.json → music).\n"
            f"3. Post this as the channel's first comment:\n\n> {pkg.get('first_comment', '')}\n\n"
            "Made for kids: No (set by the upload).")
    subprocess.run(["gh", "issue", "create", "--repo", REPO, "--title", f"Uploaded: {pkg['title']}", "--body", body], check=True)


if __name__ == "__main__":
    main()
