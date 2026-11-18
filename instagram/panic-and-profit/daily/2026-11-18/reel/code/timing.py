"""Timing for the Panic & Profit Reel of 2026-11-18 (Nvidia: CEO out, record quarter). Seconds."""
FPS = 60
DURATION = 31.6
BOUNDS = [0.0, 4.6, 11.75, 22.5, 29.55]   # hook | panic | profit | lesson | end card
EVENTS = {
    "ceo_out": 0.35, "chip": 2.0, "record": 2.7,
    "card1": 5.4, "card2": 7.6, "ticker": 9.75,
    "rev_start": 12.5, "rev_end": 15.2, "yoy": 16.1, "bar_exp": 17.8, "bar_act": 18.5, "guide": 20.6,
    "lesson_title": 22.75, "col_left": 23.6, "col_right": 25.0, "held": 26.45,
    "end_logo": 29.8,
}
HANDLE = "@panic.and.profit"
