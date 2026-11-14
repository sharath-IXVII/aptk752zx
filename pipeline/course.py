"""Course chapters (hand-written lessons rendered from the blend repo) -> YouTube.

python -m pipeline.course next            prints the next episode file to render (or nothing)
python -m pipeline.course upload EP DIR   uploads DIR/video_final.mp4 (+ DIR/thumb.jpg), adds it to
                                          the episode's playlist, records it in state/course.json
One chapter a day: each upload is scheduled at COURSE_TIME (IST, default 19:30) on the day after
the last scheduled chapter. COURSE_PUBLISH_NOW=1 makes this one public at once.
"""
import datetime as dt, json, os, sys
from pathlib import Path
from pipeline import youtube_upload as yt

STATE = Path("state/course.json")
IST = dt.timezone(dt.timedelta(hours=5, minutes=30))


def load():
    return json.loads(STATE.read_text()) if STATE.exists() else {"done": {}, "last_slot": None}


def next_episode(order: Path) -> str:
    st = load()
    if st.get("redo"):  # a chapter marked for re-upload goes first
        return st["redo"]
    if st.get("blocked"):  # a chapter the reviewer could not fix: wait for the owner, keep the order
        return ""
    done = st["done"]
    return next((e for e in json.loads(order.read_text()) if e not in done), "")


def slot(state) -> dt.datetime:
    """Next free publishing time after the last scheduled chapter. COURSE_TIMES (IST), default
    three a day: 12:00, 16:00, 19:30."""
    times = [tuple(map(int, t.split(":"))) for t in (os.getenv("COURSE_TIMES") or "12:00,16:00,19:30").split(",")]
    now = dt.datetime.now(IST)
    after = max(now + dt.timedelta(minutes=40), dt.datetime.fromisoformat(state["last_slot"]) + dt.timedelta(minutes=1)) if state.get("last_slot") else now + dt.timedelta(minutes=40)
    day = after.date()
    while True:
        for hh, mm in times:
            s = dt.datetime.combine(day, dt.time(hh, mm), IST)
            if s >= after:
                return s
        day += dt.timedelta(days=1)


def upload(ep: str, ep_path: Path, d: Path):
    state = load()
    meta = json.loads(ep_path.read_text())["yt"]
    os.environ["YT_PRIVACY"] = "public"
    when = None if os.getenv("COURSE_PUBLISH_NOW") == "1" else slot(state)
    redo = state.get("redo") == ep and ep in state["done"]
    position = None
    if redo:  # re-upload a fixed chapter (the owner deletes the old upload): same publish time, same playlist place
        when = dt.datetime.fromisoformat(state["done"][ep]["publish"])
        if when <= dt.datetime.now(IST) + dt.timedelta(minutes=20):
            when = None
        order = json.loads((ep_path.parent / "order.json").read_text())
        position = order.index(ep)
    thumb = d / "thumb.jpg"
    vid = yt.upload(d / "video_final.mp4", thumb if thumb.exists() else None, meta, publish_at=when)
    yt.add_to_playlist(vid, meta.get("playlist") or "Network Theory", position)
    state["done"][ep] = {"id": vid, "publish": (when or dt.datetime.now(IST)).isoformat()}
    if redo:
        state.pop("redo", None)
    else:
        state["last_slot"] = (when or dt.datetime.now(IST)).isoformat()
    STATE.parent.mkdir(exist_ok=True)
    STATE.write_text(json.dumps(state, indent=1))
    print(f"https://youtu.be/{vid} publish={state['last_slot']}")


if __name__ == "__main__":
    import logging; logging.basicConfig(level=logging.INFO)
    if sys.argv[1] == "block":
        st = load(); st["blocked"] = sys.argv[2]; STATE.parent.mkdir(exist_ok=True); STATE.write_text(json.dumps(st, indent=1))
    elif sys.argv[1] == "next":
        print(next_episode(Path(sys.argv[2])))
    else:
        upload(sys.argv[2], Path(sys.argv[3]), Path(sys.argv[4]))
