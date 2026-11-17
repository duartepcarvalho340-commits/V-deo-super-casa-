"""Editable timing for the Duolingo spec film. All times in seconds.
Scene boundaries follow the approved narration (audio/voice_timing.json)."""

FPS = 60
DURATION = 21.0

SCENES = {
    "intro":    (0.0, 1.5),    # Duo bounces in, trail reveals the wordmark
    "path":     (1.5, 3.0),    # trail passes lesson nodes into the first card
    "lesson":   (3.0, 5.0),    # tiles settle, answer checked, progress fills
    "streak":   (5.0, 7.2),    # trail curls into a flame, day counter climbs
    "league":   (7.2, 9.3),    # fictional learner climbs to first place
    "speak":    (9.3, 11.5),   # trail becomes a voice waveform
    "skills":   (11.5, 14.5),  # trail branches into four skill stations
    "resolve":  (14.5, 19.0),  # branches converge, message, Duo + wordmark
    "endcard":  (19.0, 21.0),  # creator card, held for the full two seconds
}

# key words in the narration -> visual events
EVENTS = {
    "lesson_node_1": 1.75, "lesson_node_2": 2.05, "lesson_node_3": 2.35,
    "tile_1": 3.15, "tile_2": 3.35, "tile_3": 3.55, "check": 3.95, "correct": 4.1,
    "flame": 5.2, "counter_start": 5.45, "counter_end": 6.9,
    "climb_start": 7.6, "climb_end": 8.55,
    "wave_start": 9.55, "wave_end": 11.2,
    "station_languages": 12.15, "station_numbers": 12.75, "station_music": 13.4, "station_chess": 13.95,
    "converge": 14.45, "msg_1": 15.1, "msg_2": 16.25, "duo_land": 17.45, "wordmark": 17.85,
    "to_endcard": 18.7,
}

NAME = "Duarte Carvalho"
HANDLE = "@duartecarvalho"
AVATAR_INITIALS = "DC"
