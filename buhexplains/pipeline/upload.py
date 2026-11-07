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
SLOTS_CENTRAL = [(12, 0), (18, 0)]   # two posts a day (owner, 2026-11-06): about noon and about 6 PM Central
# After the 0-view scare (2026-11-07 research): restart at 1 a day, published at a varied time, then go back to 2
# by setting the repo variable YT_PER_DAY=2. Fixed-time robotic posting is one of the "mass-produced" signals.
PER_DAY = int(os.environ.get("YT_PER_DAY", "1") or 1)
WINDOW_CENTRAL = ((11, 0), (19, 30))  # with 1 a day, publish at a random time in this window


def enabled() -> tuple[bool, str]:
    need = ("YT_CLIENT_ID", "YT_CLIENT_SECRET", "YT_REFRESH_TOKEN", "YT_CHANNEL_ID")
    missing = [k for k in need if not os.environ.get(k, "").strip()]
    if os.environ.get("YT_ENABLED", "").strip().lower() != "true":
        missing.append("YT_ENABLED=true")
    return (not missing, ", ".join(missing))


def uploads() -> dict:
    return json.loads(UPLOADS.read_text()) if UPLOADS.exists() else {}


def save_uploads(done: dict, msg: str) -> None:
    """Write uploads.json, commit, and push to the branch this run is on, rebasing and retrying if main moved
    (the producer pushes to main too). Never loses a record: an unsaved upload would be retried as a duplicate."""
    UPLOADS.write_text(json.dumps(done, indent=1) + "\n")
    ref = os.environ.get("GITHUB_REF_NAME", "")
    subprocess.run(["git", "add", str(UPLOADS)], check=True)
    subprocess.run(["git", "commit", "-m", msg], check=True)
    if not ref: return
    for attempt in range(5):
        if subprocess.run(["git", "push", "origin", f"HEAD:{ref}"]).returncode == 0: return
        subprocess.run(["git", "pull", "--rebase", "origin", ref], check=True)
    sys.exit("could not push uploads.json after 5 tries")


def publish_at(slot: int = 0) -> str | None:
    if os.environ.get("YT_AUTOPUBLISH", "true").strip().lower() == "false":
        return None
    import random
    from zoneinfo import ZoneInfo
    tz = ZoneInfo("America/Chicago"); now = dt.datetime.now(dt.timezone.utc).astimezone(tz)
    if PER_DAY == 1:
        (h0, m0), (h1, m1) = WINDOW_CENTRAL
        lo, hi = h0 * 60 + m0, h1 * 60 + m1
        mins = random.randint(lo, hi)
        at = now.replace(hour=mins // 60, minute=mins % 60, second=0, microsecond=0)
    else:
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
    from google.auth.transport.requests import Request
    from google.auth.exceptions import RefreshError
    creds = Credentials(None, refresh_token=os.environ["YT_REFRESH_TOKEN"], client_id=os.environ["YT_CLIENT_ID"],
                        client_secret=os.environ["YT_CLIENT_SECRET"], token_uri="https://oauth2.googleapis.com/token")
    try:
        creds.refresh(Request())
    except RefreshError as e:
        sys.exit(f"YT_REFRESH_TOKEN no longer works ({e}). If the Google Cloud OAuth consent screen is still in 'Testing', "
                 "its tokens expire after 7 days: publish the app ('In production') and re-authorize once "
                 "(docs/youtube-setup.md), then replace the YT_REFRESH_TOKEN secret.")
    return build("youtube", "v3", credentials=creds, cache_discovery=False)


QUEUE = ROOT / "buhexplains" / "queue.txt"
PAUSED = ROOT / "buhexplains" / "PAUSED"


def central_today() -> str:
    """Today's date in US Central (the owner's time zone; UTC-6 in winter, UTC-5 in summer)."""
    from zoneinfo import ZoneInfo
    return dt.datetime.now(ZoneInfo("America/Chicago")).date().isoformat()


def next_slug(done: dict) -> str | None:
    """The first slug in queue.txt (deadline order) that isn't uploaded yet and has an episode folder."""
    for line in QUEUE.read_text().splitlines():
        s = line.split("#")[0].strip()
        if s and s not in done and (EP / s / "package.json").exists():
            return s
    return None


def main() -> None:
    ap = argparse.ArgumentParser(); ap.add_argument("--slug", default=""); ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()
    ok, missing = enabled()
    if not ok:
        print(f"uploads are off (missing: {missing}). Nothing done.")
        return
    if PAUSED.exists():   # owner, 2026-11-07: "Pause for now" (0 views, possible suppression). Delete the file to resume.
        print(f"uploads are paused ({PAUSED.relative_to(ROOT)}): {PAUSED.read_text().strip()} Nothing done.")
        return
    if not a.slug:  # the daily clock (cron-job.org): one video a day, the next one in the queue
        done0 = uploads()
        n_today = sum(1 for e in done0.values() if e.get("uploaded_central") == central_today())
        if n_today >= PER_DAY:
            print(f"already uploaded {n_today} today ({central_today()}, Central; the limit is {PER_DAY}). Nothing done."); return
        a.slug = next_slug(done0) or ""
        if not a.slug:
            print("queue.txt is empty: everything is uploaded. Nothing done."); return
        print("next in queue:", a.slug)
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
        slot = sum(1 for e in done.values() if e.get("uploaded_central") == central_today())
        when = publish_at(slot)
        desc = pkg["description"] if "#shorts" in pkg["description"].lower() else pkg["description"].rstrip() + "\n\n#Shorts"
        body = {"snippet": {"title": pkg["title"], "description": desc, "categoryId": "24"},
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
    done[a.slug] = {"video_id": vid, "uploaded": today, "uploaded_central": central_today(), "title": pkg["title"], "publish_at": when}
    save_uploads(done, f"uploads: {a.slug}")
    body = (f"**{a.slug}** is uploaded to @BuhExplains (private"
            + (f", goes public at {when} UTC on its own" if when else "") + f").\n\n"
            f"1. Watch it: https://studio.youtube.com/video/{vid}/edit\n"
            f"2. Add the trending song in YouTube's editor if this episode leaves room for one (episode.json → music).\n"
            f"3. The channel's first comment is posted automatically once it's public (comment.py):\n\n> {pkg.get('first_comment', '')}\n\n"
            "Made for kids: No (set by the upload).")
    subprocess.run(["gh", "issue", "create", "--repo", REPO, "--title", f"Uploaded: {pkg['title']}", "--body", body], check=True)


if __name__ == "__main__":
    main()
