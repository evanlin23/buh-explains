"""Read-only: what YouTube reports for each uploaded video (visibility, processing, restrictions, views).

  python buhexplains/pipeline/ytstatus.py            # every video in uploads.json
Runs on Actions (status.yml), which holds the YouTube secrets. Changes nothing.
"""
import json, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
import upload

ids = {v["video_id"]: k for k, v in upload.uploads().items()}
yt = upload.youtube()
r = yt.videos().list(part="status,contentDetails,statistics,processingDetails,snippet", id=",".join(ids)).execute()
seen = set()
for v in r.get("items", []):
    seen.add(v["id"]); s, c, st = v["status"], v["contentDetails"], v.get("statistics", {})
    print(f"== {ids[v['id']]}  https://youtube.com/shorts/{v['id']}")
    print(f"  privacy={s.get('privacyStatus')} upload={s.get('uploadStatus')} publishAt={s.get('publishAt')} published={v['snippet'].get('publishedAt')}")
    print(f"  rejection={s.get('rejectionReason')} failure={s.get('failureReason')} madeForKids={s.get('madeForKids')} embeddable={s.get('embeddable')}")
    print(f"  regionRestriction={c.get('regionRestriction')} ytRating={c.get('contentRating', {}).get('ytRating')} duration={c.get('duration')} definition={c.get('definition')}")
    print(f"  processing={v.get('processingDetails', {}).get('processingStatus')} views={st.get('viewCount')} likes={st.get('likeCount')} comments={st.get('commentCount')}")
for i in set(ids) - seen:
    print(f"== {ids[i]} {i}: NOT RETURNED (deleted, or not visible to this channel)")
ch = yt.channels().list(part="status,statistics", mine=True).execute()["items"][0]
print("channel:", json.dumps({**ch["status"], **ch["statistics"]}))
