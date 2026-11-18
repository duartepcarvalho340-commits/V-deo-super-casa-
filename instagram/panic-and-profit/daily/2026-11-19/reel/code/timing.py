"""Timing for the Panic & Profit Reel of 2026-11-18 (Fed hike odds). Seconds. Matches audio/voice_timing.json."""
FPS = 60
DURATION = 30.0
# scene boundaries (vertical feed scroll between them)
BOUNDS = [0.0, 3.35, 9.65, 14.15, 18.62, 25.05, 27.95]
EVENTS = {
    "card_in": 0.15, "line1": 0.55, "line2": 1.05, "line3": 1.75,
    "tl_1": 3.75, "tl_2": 4.45, "tl_3": 6.20, "tl_4": 7.55,
    "ring_start": 10.2, "ring_end": 12.4,
    "beam_tilt": 15.55, "beam_tilt_end": 16.7,
    "bars_in": 18.85, "bar3_start": 20.35, "bar3_end": 21.3, "bar5_start": 23.15, "bar5_end": 24.1,
    "dur_start": 25.45, "dur_end": 26.9,
    "end_logo": 28.2,
}
HANDLE = "@panic.and.profit"
