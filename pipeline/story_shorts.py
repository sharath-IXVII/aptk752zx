"""Story Shorts for the course playlist (Volt the mascot), two a day.
python -m pipeline.story_shorts next <order.json>         prints the next Short file (or nothing)
python -m pipeline.story_shorts upload EP <ep.json> <video>   uploads it, scheduled at SHORT_TIMES (IST)
The description links to the matching full chapter when it is already uploaded (state/course.json)."""
import datetime as dt, json, os, sys
from pathlib import Path
from pipeline import youtube_upload as yt

STATE = Path("state/story_shorts.json"); COURSE = Path("state/course.json")
IST = dt.timezone(dt.timedelta(hours=5, minutes=30))
load = lambda: json.loads(STATE.read_text()) if STATE.exists() else {"done": {}, "last_slot": None}


def slot(state) -> dt.datetime:
    times = [tuple(map(int, t.split(":"))) for t in (os.getenv("SHORT_TIMES") or "10:00,17:00").split(",")]
    now = dt.datetime.now(IST); after = now + dt.timedelta(minutes=40)
    if state.get("last_slot"):
        after = max(after, dt.datetime.fromisoformat(state["last_slot"]) + dt.timedelta(minutes=1))
    day = after.date()
    while True:
        for hh, mm in times:
            s = dt.datetime.combine(day, dt.time(hh, mm), IST)
            if s >= after:
                return s
        day += dt.timedelta(days=1)


def upload(key: str, ep_path: Path, video: Path) -> None:
    state = load(); ep = json.loads(ep_path.read_text()); meta = dict(ep["yt"])
    course = json.loads(COURSE.read_text()) if COURSE.exists() else {"done": {}}
    full = course["done"].get(ep.get("links", ""))
    if full:
        meta["description"] = f"▶ Full video: https://youtu.be/{full['id']}\n" + meta["description"]
    os.environ["YT_PRIVACY"] = "public"
    when = slot(state)
    vid = yt.upload(video, None, meta, publish_at=when)
    state["done"][key] = {"id": vid, "publish": when.isoformat()}; state["last_slot"] = when.isoformat()
    STATE.parent.mkdir(exist_ok=True); STATE.write_text(json.dumps(state, indent=1))
    print(f"https://youtu.be/{vid} publish={when.isoformat()}")


if __name__ == "__main__":
    import logging; logging.basicConfig(level=logging.INFO)
    if sys.argv[1] == "next":
        done = load()["done"]
        print(next((e for e in json.loads(Path(sys.argv[2]).read_text()) if e not in done), ""))
    else:
        upload(sys.argv[2], Path(sys.argv[3]), Path(sys.argv[4]))
