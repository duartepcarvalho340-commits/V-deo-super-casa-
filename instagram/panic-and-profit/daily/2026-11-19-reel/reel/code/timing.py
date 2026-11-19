"""Timing for the Anthropic IPO Reel (2026-11-19). Derived from audio/voice_timing.json so it follows the voice."""
import json, os
FPS = 60
_T = json.load(open(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "audio/voice_timing.json")))
P = [p["t0"] for p in _T]; PE = [p["t1"] for p in _T]
N_PE = 4             # P/E explainer phrases (indices 6..9)
FT_IDX = 6 + N_PE    # opening-price phrase
LIVE = FT_IDX + 1      # 4 live-update phrases: LIVE..LIVE+3
CLOSE = len(P) - 2   # "Day one is the headline..." ; last phrase = closing question
END = PE[-1] + 0.6
DURATION = round(END + 2.1, 2)
HANDLE = "@panic.and.profit"
# first-trade row: set FIRST_TRADE env as "91.20|+9.9%" once ANT has opened; empty = "trading starts today"
FT = os.environ.get("FIRST_TRADE", "")
