"""Reviewer AI for hand-written course chapters - checks AND fixes before rendering.

1. A strict professor AI reviews every scene (facts, formulas, units, flow, narration vs animation).
2. Every issue it finds is fixed by the AI itself (corrected scene JSON), then the chapter is
   reviewed again - up to 3 rounds.
3. If critical mistakes remain, the chapter is NOT rendered/uploaded: the run fails and a GitHub
   issue is opened (GitHub emails the owner).
python -m pipeline.course_review <episode.json>     (writes the corrected episode in place)
"""
import json, os, sys
from pathlib import Path
from pipeline import llm

REVIEWER_MODEL = os.getenv("REVIEWER_MODEL") or "deepseek-ai/deepseek-v4.1-flash"

REVIEW = """You are a strict senior professor of Electronics & Communication Engineering reviewing a
beginner video lesson before it is published. Students know NOTHING. Each scene is an animation
(its "type" and fields decide what is drawn: numbers in fields are what appears on screen) plus
the "narration" spoken over it. Check every scene:
1. Facts, numbers, formulas, units, directions, component behaviour: 100% correct?
2. Narration matches what the animation fields show (same values, same names, same order)?
3. Every new term explained before or when it is used? Smooth bridge from the previous topic?
4. Anything important for students missing from this topic?
Report only REAL problems. "critical" = wrong or misleading or mismatched with the screen;
"minor" = clarity/flow. Reply JSON only:
{"issues":[{"scene":<index>,"severity":"critical|minor","problem":"...","fix":"..."}],"missing":["..."]}"""

FIX = """You are the same professor. Fix the listed problems in these scenes. Return the corrected
scenes as JSON: {"scenes":{"<index>": <full corrected scene object>}}.
Rules: keep "type" and "chapter" unchanged; keep the same field names; change only what is needed;
narration stays clear, friendly and spoken (no markdown), explaining through the animation
("watch", "see", "notice"); numbers in narration must match the fields."""


def review(ep: dict) -> dict:
    scenes = [{"i": i, **s} for i, s in enumerate(ep["scenes"])]
    return llm.chat_json(f"Lesson: {ep['title']}\n\nScenes:\n{json.dumps(scenes, ensure_ascii=False)}",
                         system=REVIEW, temperature=0.1, max_tokens=4000, prefer=REVIEWER_MODEL)


def fix(ep: dict, issues: list) -> int:
    idx = sorted({int(i["scene"]) for i in issues if str(i.get("scene", "")).isdigit() and int(i["scene"]) < len(ep["scenes"])})
    if not idx:
        return 0
    ask = {"problems": issues, "scenes": {str(i): ep["scenes"][i] for i in idx}}
    out = llm.chat_json(json.dumps(ask, ensure_ascii=False), system=FIX, temperature=0.2,
                        max_tokens=6000, prefer=REVIEWER_MODEL).get("scenes", {})
    n = 0
    for k, new in out.items():
        i = int(k)
        old = ep["scenes"][i]
        if not isinstance(new, dict) or new.get("type") != old["type"] or not new.get("narration"):
            continue
        new["chapter"] = old.get("chapter", new.get("chapter"))
        ep["scenes"][i] = {**old, **new}
        n += 1
    return n


def main(path: Path) -> None:
    ep = json.loads(path.read_text())
    log = []
    for rnd in range(1, 4):
        r = review(ep)
        issues = r.get("issues", [])
        crit = [i for i in issues if i.get("severity") == "critical"]
        for i in issues:
            log.append(f"round {rnd} [{i.get('severity')}] scene {i.get('scene')}: {i.get('problem')} -> {i.get('fix')}")
        for m in r.get("missing", []):
            log.append(f"round {rnd} [missing] {m}")
        if not issues:
            break
        fixed = fix(ep, issues)
        log.append(f"round {rnd}: AI fixed {fixed} scene(s)")
        if not crit and rnd >= 2:
            break
    final = review(ep)
    crit = [i for i in final.get("issues", []) if i.get("severity") == "critical"]
    path.write_text(json.dumps(ep, indent=1, ensure_ascii=False))
    Path("review_log.txt").write_text("\n".join(log + [f"final critical: {len(crit)}"] +
                                              [f"[critical] scene {i.get('scene')}: {i.get('problem')}" for i in crit]))
    print("\n".join(log))
    if crit:
        Path("review_failed.txt").write_text("\n".join(f"scene {i.get('scene')}: {i.get('problem')} -> {i.get('fix')}" for i in crit))
        sys.exit(f"Reviewer could not fix {len(crit)} critical mistake(s) - chapter NOT uploaded.")
    print("Reviewer: OK (all issues fixed)")


if __name__ == "__main__":
    main(Path(sys.argv[1]))
