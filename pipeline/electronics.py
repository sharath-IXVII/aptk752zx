"""The channel's content: "How It Works" - electronics explained for students (GetYr_ECE).

Every episode explains how one everyday device or electronics idea works (a fan, a charger,
AirPods, a laptop, where our current comes from...), accurately and in depth, from the
basic idea up to the real engineering, so any student can follow it. A writer pass, then a
strict technical fact-check pass. Topics are never repeated (state/used_topics.json).
"""

import datetime as dt
import json
import logging
import random
from pathlib import Path

from pipeline import llm

log = logging.getLogger(__name__)

SERIES = "How It Works"
USED_FILE = Path("state/used_topics.json")

TOPICS = {
    "home": [
        "ceiling fan", "electric iron", "refrigerator", "air conditioner", "microwave oven",
        "induction cooktop", "electric kettle", "water heater (geyser)", "washing machine",
        "mixer grinder", "LED bulb", "tube light", "inverter and home UPS", "doorbell",
        "electric meter", "MCB circuit breaker", "earthing (grounding) in a house",
        "house wiring", "voltage stabilizer", "smoke detector", "TV remote control",
        "LED TV", "set-top box", "Wi-Fi router", "smart plug", "motion sensor light",
        "emergency light", "water level controller", "electric motor pump", "room heater",
    ],
    "power": [
        "how electricity reaches our home", "power plant generator", "transformer",
        "solar panel", "solar inverter", "wind turbine", "hydroelectric power",
        "nuclear power plant", "power grid", "AC vs DC current", "why our supply is 230 V 50 Hz",
        "battery", "lithium-ion battery", "lead-acid car battery", "power bank",
        "fast charging", "wireless charging", "phone charger (SMPS)", "laptop charger",
        "electric vehicle battery", "EV charging station", "regenerative braking",
        "supercapacitor", "fuse", "surge protector", "three-phase power",
    ],
    "gadgets": [
        "smartphone", "AirPods and wireless earbuds", "Bluetooth", "noise cancellation",
        "laptop", "computer CPU", "RAM", "SSD", "hard disk", "keyboard", "computer mouse",
        "touchscreen", "fingerprint sensor", "face unlock", "phone camera", "smartwatch",
        "fitness band heart-rate sensor", "GPS", "speaker", "microphone", "headphones",
        "digital camera sensor", "projector", "printer", "3D printer", "drone", "VR headset",
        "game controller", "USB", "HDMI", "QR code scanner", "barcode scanner",
        "contactless card payment (NFC)", "smart speaker", "e-reader", "calculator",
    ],
    "communication": [
        "mobile network (4G and 5G)", "SIM card", "Wi-Fi", "internet", "optical fibre",
        "satellite communication", "radio", "FM vs AM radio", "television broadcast",
        "antenna", "radar", "landline telephone", "how a phone call travels", "OTP and SMS",
        "how a video call works", "how data is stored in the cloud", "how email travels",
    ],
    "components": [
        "resistor", "capacitor", "inductor", "diode", "LED", "transistor", "MOSFET",
        "integrated circuit (IC)", "microcontroller", "Arduino", "relay", "transformer coil",
        "crystal oscillator", "voltage regulator", "op-amp", "logic gates", "flip-flop",
        "555 timer", "PCB (printed circuit board)", "soldering", "semiconductor",
        "P-N junction", "rectifier", "multimeter", "oscilloscope", "sensor", "thermistor",
        "LDR light sensor", "ultrasonic sensor", "infrared sensor", "servo motor",
        "stepper motor", "DC motor", "BLDC motor", "induction motor", "electromagnet",
    ],
    "basics": [
        "electric current", "voltage", "resistance and Ohm's law", "power and energy",
        "electric charge", "magnetism and electricity", "electromagnetic induction",
        "static electricity", "lightning", "short circuit", "why birds don't get shocked",
        "why we get an electric shock", "conductors and insulators", "series and parallel circuits",
        "frequency", "electromagnetic waves", "binary numbers in computers", "analog vs digital",
        "how a chip is made", "Moore's law",
    ],
    "transport": [
        "electric car", "electric scooter", "car alternator", "car spark plug", "traffic signal",
        "metro train", "electric locomotive", "airport metal detector", "lift (elevator)",
        "escalator", "automatic doors", "toll FASTag", "speed camera", "car airbag sensor",
        "parking sensor", "car keyless entry",
    ],
}

SYSTEM = (
    "You are an expert electronics and electrical engineering teacher and the head writer "
    "of an educational YouTube channel for students in India and the US. You explain how "
    "things work accurately and in depth, with simple words, clear analogies and correct "
    "engineering, so a school or college student can truly understand."
)

VISUAL_STYLE = (
    "Animate the whole video as a clean, modern educational animation: smooth motion "
    "graphics, cutaway views that open the device to show the parts inside, labelled "
    "components, arrows and glowing particles showing current flow, magnetic fields and "
    "signals, simple circuit diagrams that build up step by step, and zoom-ins from the "
    "whole device down to the tiny parts. Bright, clear colours on a clean background. Keep "
    "everything technically correct and consistent with the narration. Every scene moves - "
    "no still slides. Use on-screen text only for the title and short labels. No logos or "
    "brand names."
)


def all_topics() -> list[str]:
    seen, out = set(), []
    for group in TOPICS.values():
        for t in group:
            if t not in seen:
                seen.add(t)
                out.append(t)
    return out


def used() -> list[str]:
    return json.loads(USED_FILE.read_text()) if USED_FILE.exists() else []


def mark_used(topic: str) -> None:
    USED_FILE.parent.mkdir(parents=True, exist_ok=True)
    USED_FILE.write_text(json.dumps(used() + [topic], indent=1, ensure_ascii=False))


def next_topic() -> str:
    done = set(used())
    left = [t for t in all_topics() if t not in done] or all_topics()
    picks = random.sample(left, min(8, len(left)))
    try:  # choose the one people search for most (more YouTube autocomplete results)
        from pipeline.packaging import search_suggestions
        scores = {t: len(search_suggestions(f"how does {t} work")) +
                  len(search_suggestions(f"{t} working")) for t in picks}
        log.info("Search interest: %s", scores)
        return max(picks, key=scores.get)
    except Exception:
        return picks[0]


def write_script(topic: str) -> dict:
    result = llm.chat_json(f"""Write the narration for an educational video: How does a
{topic} work?

Structure (spoken narration only, 800-1000 words):
1. Hook (1-2 sentences): a surprising fact or question about the {topic}.
2. What it is and what it does, in one simple sentence.
3. The basic principle (the physics or electronics idea behind it) with an everyday analogy.
4. Inside it, step by step: the main parts and exactly what each one does, following the
   path of energy / current / signal from input to output. Name the real components
   (e.g. rectifier, capacitor, MOSFET, coil, sensor, microcontroller) and explain each simply.
5. Real numbers where they help understanding (typical voltage, current, frequency, power,
   speed) - only well-established typical values.
6. A common misconception or interesting detail, and safety where relevant.
7. A 3-point quick recap and a closing line that makes students curious for the next video.

Rules: 100% technically accurate - if unsure about a detail, leave it out. Simple English for
students, explain every technical word the first time it is used. No brand names, no
scene directions, no [brackets], no emojis.

Return JSON: {{"title": "<working title>", "script": "<the full narration>"}}""",
                           SYSTEM, temperature=0.5, max_tokens=5000, prefer=llm.WRITER_MODEL)
    words = len(result.get("script", "").split())
    if words < 600:
        longer = llm.chat_json(f"""This narration is too short ({words} words). Expand it to
850-1000 words: go deeper into the inside parts and how energy/current/signals flow, keep
the same structure and accuracy.

{result.get("script", "")}

Return JSON: {{"title": "<working title>", "script": "<the full narration>"}}""",
                               SYSTEM, temperature=0.4, max_tokens=5000,
                               prefer=llm.WRITER_MODEL)
        if len(longer.get("script", "").split()) > words:
            result, words = longer, len(longer["script"].split())
    if words < 450:
        raise RuntimeError(f"Script too short ({words} words)")
    return fact_check(topic, result)


def fact_check(topic: str, result: dict) -> dict:
    """Strict technical review: find and fix every inaccurate or misleading statement."""
    try:
        r = llm.chat_json(f"""You are a strict electrical/electronics engineering professor
reviewing a student video script about how a {topic} works. Check every technical claim:
physics, component names and roles, the order of energy/signal flow, numbers and units,
and safety statements. Fix anything wrong, oversimplified to the point of being false, or
misleading. Keep the structure, length and simple spoken style.

SCRIPT:
{result["script"]}

Return JSON: {{"errors_found": ["<each problem and fix>"], "script": "<the corrected script>"}}""",
                          SYSTEM, temperature=0.2, max_tokens=5000, prefer=llm.WRITER_MODEL)
    except Exception as exc:
        log.warning("Fact-check failed, keeping the script: %s", exc)
        return result
    for e in r.get("errors_found", [])[:15]:
        log.info("Fact-check fix: %s", e)
    if len(r.get("script", "").split()) >= 450:
        result["script"] = r["script"]
    return result


def create_script() -> dict:
    topic = next_topic()
    log.info("Today's topic: %s", topic)
    result = write_script(topic)
    result.update({"topic": topic, "ece_topic": topic, "series": SERIES,
                   "visual_style": VISUAL_STYLE, "sources": [], "research": {},
                   "date": dt.date.today().isoformat()})
    return result


def make_metadata(script: dict) -> dict:
    topic = script["ece_topic"]
    return llm.chat_json(f"""You are a YouTube SEO expert for an educational electronics
channel for students (India and the US). Package this video about how a {topic} works.

SCRIPT:
{script["script"]}

Write:
- title: 40-65 characters, the way students search, curiosity + clarity, e.g.
  "How Does a Ceiling Fan Actually Work?", "What's Inside Your Phone
  Charger?", "How AirPods Work - The Tech Inside". No emojis.
- cover_text: 2-4 words for the title screen and thumbnail, e.g. "HOW FANS WORK".
- short_hook: one gripping sentence (max 12 words) for the vertical Short, e.g.
  "Your charger shrinks 230 volts into 5 - here's how."
- description: 1) two sentences with the main keywords ("how does a {topic} work"),
  2) "In this video:" with 5 short lines starting with "- " (the parts/ideas covered),
  3) a line inviting students to ask questions in the comments. No links, no hashtags.
- hashtags: 3, e.g. "#electronics", "#howitworks", "#engineering"
- tags: 15 search tags (e.g. "how {topic} works", "{topic} working principle",
  "{topic} explained", "how {topic} works inside", "ECE"), most important first.

Return JSON: {{"title": "...", "cover_text": "...", "short_hook": "...", "description": "...",
"hashtags": ["#..."], "tags": ["..."]}}""", temperature=0.5, max_tokens=2000,
                          prefer=llm.WRITER_MODEL)
