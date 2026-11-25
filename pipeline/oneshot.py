"""Analog Electronics one-shot: build the description with chapter timestamps and upload the joined video.

python -m pipeline.oneshot upload <video.mp4> <durations.json> <episodes_dir>
durations.json: {"intro": seconds, "c00_atoms": seconds, ...} (chapters in file-name order)."""
import json, os, sys
from pathlib import Path


def stamp(s: float) -> str:
    s = int(s); h, m = divmod(s, 3600); m, sec = divmod(m, 60)
    return f"{h}:{m:02d}:{sec:02d}"


def description(durs: dict, ep_dir: Path) -> str:
    t = durs.get("intro", 0.0); lines = []
    for f in sorted(ep_dir.glob("c*.json")):
        sc = json.loads(f.read_text())["scenes"][0]
        name = sc.get("chapter", f.stem).replace("Chapter ", "Ch ")
        lines.append(f"{stamp(t)} {name}")
        t += durs.get(f.stem, 0.0)
    head = ("The complete Analog Electronics course in ONE video, from zero to placement level. "
            "Every concept is shown visually with real circuits: conventional current and electron flow, "
            "what happens if you flip a diode or reverse a capacitor, every value calculated, real-world "
            "applications and solved numericals after every topic.\n\nChapters:\n")
    tail = ("\n\n#analogelectronics #electronics #ece #diodes #bjt #opamp #placement #gate")
    return head + "\n".join(lines) + tail


def upload(video: str, durs_file: str, ep_dir: str):
    from pipeline import youtube_upload as yt
    durs = json.loads(Path(durs_file).read_text())
    meta = {"title": "Analog Electronics One Shot | Complete Course From Zero to Placement Level",
            "description": description(durs, Path(ep_dir)),
            "tags": ["analog electronics", "analog electronics one shot", "electronics full course", "diodes",
                     "bjt", "mosfet", "op amp", "rectifier", "clipper", "clamper", "ece", "placement"]}
    print(meta["description"])
    if os.getenv("ONESHOT_DRY") == "1":
        return
    os.environ["YT_PRIVACY"] = "private"   # checked first, then made public
    vid = yt.upload(Path(video), None, meta)
    try:
        yt.add_to_playlist(vid, "Analog Electronics")
    except Exception as e:  # the video itself is what matters
        print("playlist:", e)
    Path("state").mkdir(exist_ok=True)
    Path("state/oneshot.json").write_text(json.dumps({"id": vid}, indent=1))
    print(f"https://youtu.be/{vid}")


if __name__ == "__main__":
    if sys.argv[1] == "upload":
        upload(*sys.argv[2:5])
