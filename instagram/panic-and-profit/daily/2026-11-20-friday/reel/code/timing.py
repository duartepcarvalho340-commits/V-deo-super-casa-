"""Timing for the Asia AI-chip Reel (2026-11-20). Derived from audio/voice_timing.json."""
import json, os
FPS = 60
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_T = json.load(open(f"{ROOT}/audio/voice_timing.json"))
NUM = json.load(open(f"{ROOT}/numbers.json"))
P = [p["t0"] for p in _T]; PE = [p["t1"] for p in _T]
END = PE[-1] + 0.5
DURATION = round(END + 2.1, 2)
HANDLE = "@panic.and.profit"
