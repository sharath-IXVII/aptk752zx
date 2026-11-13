"""Image search test: find licensed photos for a few queries (nothing is published)."""
import logging, sys
from pathlib import Path
sys.path.insert(0, ".")
logging.basicConfig(level=logging.INFO, format="%(message)s")
from pipeline import studio
ep = {"scenes": [{"type": "image", "query": q, "narration": f"This is a {q}. It is shown here."} for q in
      ("printed circuit board", "bridge rectifier", "Great Wall of China", "Indian rupee coins")]}
credits = studio.fetch_images(ep, Path("studio/explainer"))
for sc in ep["scenes"]: print(sc.get("type"), sc.get("src"), sc.get("credit"))
print("\n".join(credits))
