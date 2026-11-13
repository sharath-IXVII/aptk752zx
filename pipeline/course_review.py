"""Second-opinion review of a hand-written course chapter BEFORE it is rendered.
A strict teacher AI reads every scene and reports real mistakes (wrong facts, wrong formulas,
wrong units, broken flow, jargon used before it is explained). Any 'critical' issue stops the
run, so a chapter with a mistake is never uploaded. Writes review.json next to the episode.
python -m pipeline.course_review episodes/network/p1_resistor.json
"""
import json, sys
from pathlib import Path
from pipeline import llm
import os
REVIEWER_MODEL = os.getenv("REVIEWER_MODEL") or "deepseek-ai/deepseek-v4.1-flash"

SYSTEM = """You are a strict senior professor of Electronics & Communication Engineering reviewing
a beginner video lesson before it is published. Students know NOTHING. Check every scene:
1. Facts, numbers, formulas, units, directions of current, component behaviour: 100% correct?
2. Is every new term explained before (or when) it is used?
3. Does each topic connect smoothly to the previous one?
4. Does the narration match what the animation shows (the scene type and its fields)?
5. Is anything important for students missing from this topic?
Only report REAL problems. Severity: "critical" = factually wrong or misleading; "minor" = clarity/flow.
Reply JSON only: {"issues":[{"scene":<index>,"severity":"critical|minor","problem":"...","fix":"..."}],
"missing":["..."],"verdict":"ok|fix"}"""


def review(path: Path) -> dict:
    ep = json.loads(path.read_text())
    scenes = [{"i": i, **{k: v for k, v in s.items()}} for i, s in enumerate(ep["scenes"])]
    out = llm.chat_json(f"Lesson: {ep['title']}\n\nScenes:\n{json.dumps(scenes, ensure_ascii=False)}",
                        system=SYSTEM, temperature=0.1, max_tokens=4000, prefer=REVIEWER_MODEL)
    return out


if __name__ == "__main__":
    p = Path(sys.argv[1]); r = review(p)
    Path("review.json").write_text(json.dumps(r, indent=1, ensure_ascii=False))
    crit = [i for i in r.get("issues", []) if i.get("severity") == "critical"]
    for i in r.get("issues", []): print(f"[{i.get('severity')}] scene {i.get('scene')}: {i.get('problem')} -> {i.get('fix')}")
    for m in r.get("missing", []): print("[missing]", m)
    if crit:
        sys.exit(f"Reviewer found {len(crit)} critical mistake(s) - not rendering this chapter.")
    print("Reviewer: OK")
