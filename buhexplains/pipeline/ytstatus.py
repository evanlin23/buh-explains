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
pl = yt.channels().list(part="contentDetails", mine=True).execute()["items"][0]["contentDetails"]["relatedPlaylists"]["uploads"]
items = yt.playlistItems().list(part="snippet,status", playlistId=pl, maxResults=50).execute().get("items", [])
extra = [i for i in items if i["snippet"]["resourceId"]["videoId"] not in ids]
if extra:
    st = {v["id"]: v for v in yt.videos().list(part="status,statistics", id=",".join(i["snippet"]["resourceId"]["videoId"] for i in extra)).execute().get("items", [])}
    print("other videos on the channel (not in uploads.json):")
    for i in extra:
        vid = i["snippet"]["resourceId"]["videoId"]; v = st.get(vid, {})
        print(f"  {vid}  {i['snippet']['publishedAt']}  {v.get('status', {}).get('privacyStatus')}  views={v.get('statistics', {}).get('viewCount')}  {i['snippet']['title']!r}")
ch = yt.channels().list(part="status,statistics", mine=True).execute()["items"][0]
print("channel:", json.dumps({**ch["status"], **ch["statistics"]}))
