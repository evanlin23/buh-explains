"""Post each uploaded episode's first comment (package.json "first_comment") as the channel, once it's public.

    python buhexplains/pipeline/comment.py [--dry-run]

YouTube's API can't pin, so the channel's own first comment carries the text. Needs the `youtube.force-ssl` scope on
the refresh token (docs/youtube-setup.md). Each video gets one comment, recorded as "commented" in uploads.json.
Run by comments.yml (cron-job.org, after the noon and 6 PM publish slots) and as a catch-up at the end of every upload run.
"""
from __future__ import annotations

import argparse, json, sys

from upload import EP, UPLOADS, enabled, save_uploads, uploads, youtube


def main() -> int:
    ap = argparse.ArgumentParser(); ap.add_argument("--dry-run", action="store_true"); a = ap.parse_args()
    ok, missing = enabled()
    if not ok:
        print(f"uploads are off (missing: {missing}), so no comments either. Nothing done."); return 0
    done = uploads()
    ids = [e["video_id"] for e in done.values() if e.get("video_id") and not e.get("commented")]
    if not ids:
        print("nothing to comment on"); return 0
    yt = youtube()
    items = yt.videos().list(part="status", id=",".join(ids[:50])).execute().get("items", [])
    status = {v["id"]: v["status"]["privacyStatus"] for v in items}
    posted = []
    for slug, e in done.items():
        if not e.get("video_id") or e.get("commented") or status.get(e["video_id"]) != "public":
            continue
        text = str(json.loads((EP / slug / "package.json").read_text()).get("first_comment", "")).strip()
        if not text: continue
        print(f"{slug}: commenting on {e['video_id']}: {text!r}")
        if a.dry_run: continue
        try:
            yt.commentThreads().insert(part="snippet", body={"snippet": {"videoId": e["video_id"], "topLevelComment": {
                "snippet": {"textOriginal": text}}}}).execute()
        except Exception as ex:  # most likely: the refresh token lacks the youtube.force-ssl scope
            print(f"could not comment on {slug}: {ex}\n(if this says insufficient scope: re-authorize with youtube.force-ssl, docs/youtube-setup.md)")
            return 1
        e["commented"] = True; posted.append(slug)
    if posted:
        save_uploads(done, f"comments: {', '.join(posted)}")
    waiting = [s for s, e in done.items() if e.get("video_id") and not e.get("commented")]
    print(f"waiting to go public: {waiting}" if waiting else "all comments posted")
    return 0


if __name__ == "__main__":
    sys.exit(main())
