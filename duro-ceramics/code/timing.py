"""Editable timing for the Duro Ceramics spec film ("Da roda à mesa"). All times in seconds."""

FPS = 60
DURATION = 21.0
BPM = 80; BEAT = 60 / BPM; BAR = 4 * BEAT; MUSIC_T0 = 0.30   # bars land on 0.30, 3.30, 6.30 ... 18.30

# narration (start, text, tempo or None for the default 1.07) -- PT-PT, voice "Ines"
VOICE_PT = [
    (0.35, "Nas Caldas da Rainha, tudo começa no barro.", None),
    (3.60, "Moldado à mão.", None),
    (5.30, "Pintado à mão, pincelada a pincelada.", None),
    (8.60, "Sardinhas que saltam para a mesa.", None),
    (10.95, "E andorinhas que voltam sempre a casa.", None),
    (13.95, "Cerâmica portuguesa. Feita para durar.", None),
    (17.35, "Duro Ceramics.", 1.0),
]

EV = {
    # 1 · the wheel
    "clay_drop": 0.06, "clay_land": 0.30, "centre_end": 1.85, "open_start": 1.85, "open_end": 3.35,
    "groove": 3.70, "glaze": 4.40, "glaze_end": 5.15,
    # 2 · the brush (banding wheel)
    "brush_in": 5.05, "ring": 5.35, "ring_end": 5.95, "fish0": 6.05, "fish_dur": 0.30, "dots": 7.85, "brush_out": 8.20,
    # 3 · the table
    "lift": 8.45, "set": 8.85, "zoom": 8.70, "zoom_end": 9.85, "items": 8.95, "jump": 9.30, "jump_end": 9.95,
    "shadow_pass": 10.20, "whip": 10.70, "whip_end": 11.05,
    # 4 · the wall
    "sw0": 11.25, "sw1": 11.60, "sw2": 11.95, "takeoff": 13.30, "takeover": 13.55, "takeover_end": 13.92,
    # 5 · the stack + logo
    "drops": [14.175, 14.55, 14.925, 15.30], "white": 15.675, "logo": 16.20, "logo_end": 17.10, "ring_text": 16.95,
    "essence": 17.50, "flip": 18.45, "flip_end": 18.92, "card": 18.92,
}

TEXT = {
    "pt": {
        "kicker": "CALDAS DA RAINHA · PORTUGAL",
        "h1": [("Tudo começa", "serif"), ("no barro.", "ital")],
        "h2": [("Moldado", "serif"), ("à mão.", "ital")],
        "h3": [("Pintado", "serif"), ("à mão,", "ital")], "h3_script": "pincelada a pincelada",
        "h4": [("Sardinhas que saltam", "serif"), ("para a mesa.", "ital")],
        "h5": [("Andorinhas que voltam", "serif"), ("sempre a casa.", "ital")],
        "k6": "CERÂMICA PORTUGUESA", "h6": [("Feita para", "serif"), ("durar.", "ital")],
        "ring": "FEITO À MÃO  ·  CALDAS DA RAINHA  ·  PORTUGAL  ·  ",
        "essence": "Novas leituras do artesanato português",
        "disclaimer": "Conceito independente · sem afiliação à Duro Ceramics",
    },
}

NAME = "Duarte Carvalho"
HANDLE = "@duartecarvalho"
MONOGRAM = "DC"
