"""Timing for the Retail earnings Reel (2026-11-20). Derived from audio/voice_timing.json."""
import json, os
FPS = 60
_T = json.load(open(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "audio/voice_timing.json")))
P = [p["t0"] for p in _T]; PE = [p["t1"] for p in _T]
END = PE[-1] + 0.5
DURATION = round(END + 2.1, 2)
HANDLE = "@panic.and.profit"
# market numbers (set after the close): AMD_CLOSE="-6.1%", SOX_CLOSE="-2.4%", NDX_CLOSE="-0.5%"
AMD_CLOSE = os.environ.get("AMD_CLOSE", "")
SOX_CLOSE = os.environ.get("SOX_CLOSE", "")
NDX_CLOSE = os.environ.get("NDX_CLOSE", "")
