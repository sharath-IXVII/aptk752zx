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

SCENES = """WHAT EACH SCENE TYPE DRAWS (all of this IS on screen - never ask to "verify" it):
- dc: a circuit (battery v, resistors r[], series/parallel) with electrons moving; show "current" = ammeter
  reading (computed V/R), "voltage" = a voltmeter on each resistor, "heat" = resistor glow; v_to sweeps the voltage.
- inside: zoom into a material: atoms + drifting electrons that visibly collide (mode wire/resistor/insulator/no-voltage).
- atom: Bohr-style atom with nucleus and electron shells. water: two tanks + pipe (voltage analogy).
- ohm: live I-vs-V graph (V on x-axis, I on y-axis) with one labelled line per resistor.
- formula: the formula in big text, each term with its meaning, and the example lines.
- bars: labelled horizontal bars with values. steps: numbered list. diagram: labelled boxes with arrows; steps highlight boxes.
- resistor: mode bands = resistor body with the listed colour bands, each band labelled (colour, digit/multiplier/tolerance)
  and the final value; cutaway = leads, end caps, ceramic core, carbon film, spiral cut, coating, each labelled;
  pot = potentiometer knob, wiper, live resistance value and a lamp whose brightness follows the current.
- capacitor: two plates, dielectric, charges piling up, % stored. rc: RC circuit + live Vc/I meters + exponential graph with 1τ mark.
- capgeom: plates growing / moving closer / dielectric sliding in with a capacitance bar.
- coil: field = coil with growing magnetic field loops and current value; magnet = magnet moving in/out of a coil with a meter needle.
- rl: RL circuit with switch, current meter and graph; off = switch opens with a spark.
- source: ideal/practical voltage or current source with a shrinking load, live meters and a V-I graph.
- net: one example circuit (battery + R1..R4) highlighting nodes / branches / loops / meshes, or open / short.
- kcl: a node with labelled currents in/out and an In = Out tally. kvl: a marker walking a loop with a running sum of rises and drops.
- wave: oscilloscope with AC input and (cap=true) smoothed output with ripple. lab-title / lab-outro: title and next-part cards."""

REVIEW = """You are a strict senior professor of Electronics & Communication Engineering reviewing a
beginner video lesson before it is published. Students know NOTHING. Each scene is an animation
(its "type" and fields decide what is drawn) plus the "narration" spoken over it.

""" + SCENES + """

Report ONLY real problems you are SURE about:
- "critical": a fact, number, formula, unit or direction that is WRONG, or narration that contradicts
  the scene's fields (different value/name/order). You must be able to state the exact wrong statement
  and the exact correct one.
- "minor": a genuinely confusing or missing explanation for a beginner.
NEVER report something you checked and found correct. NEVER ask to "verify", "ensure" or "confirm"
the animation - the list above tells you exactly what is drawn. Simplifications that are standard in
beginner teaching are fine. If the lesson is correct, return an empty issues list.
Reply JSON only:
{"issues":[{"scene":<index>,"severity":"critical|minor","problem":"...","fix":"..."}],"missing":["..."]}"""

FIX = """You are the same professor. Fix the listed problems in these scenes. Return the corrected
scenes as JSON: {"scenes":{"<index>": <full corrected scene object>}}.
Rules: keep "type" and "chapter" unchanged; keep the same field names and do not add new fields
(the animation cannot show captions or anything not listed); change only what is needed;
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


CHECKER_MODEL = os.getenv("CHECKER_MODEL") or "qwen/qwen3-235b-a22b"
CHECK = """You are a careful physics/electronics examiner. A reviewer claims a statement in a beginner
lesson is wrong. Decide if the ORIGINAL statement is actually factually wrong (wrong fact, number,
formula, unit or direction), showing your calculation. Unclear wording, style, order of words, or a
correct simplification is NOT wrong. Reply JSON only: {"wrong": true|false, "why": "..."}"""


def confirmed(ep: dict, issue: dict) -> bool:
    """A second, independent model must confirm a critical mistake before it can stop a chapter."""
    try:
        i = int(issue.get("scene"))
        scene = ep["scenes"][i]
    except (TypeError, ValueError, IndexError):
        return False
    try:
        r = llm.chat_json(json.dumps({"scene": scene, "claimed_problem": issue.get("problem")}, ensure_ascii=False),
                          system=CHECK, temperature=0, max_tokens=1500, prefer=CHECKER_MODEL)
        return bool(r.get("wrong"))
    except Exception:
        return False


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
    crit = [i for i in crit if confirmed(ep, i)]  # drop the reviewer's false alarms
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
