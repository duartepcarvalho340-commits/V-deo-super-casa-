"""Timing and on-screen text for the Panic & Profit launch reel. All times in seconds.
Times follow the narration in audio/voice_timing_en.json (ElevenLabs voice "Emily" via Higgsfield)."""

FPS = 60
DURATION = 21.0

SCENES = {
    "panic":    (0.0, 3.55),   # headline slips slam in, stack and tremble; red chart falls
    "turn":     (3.55, 6.15),  # slips fall away; "Every headline moves your money."
    "flip":     (6.15, 8.4),   # one slip returns, flips over and opens into the explainer
    "explain":  (8.4, 11.3),   # 01 Geopolitics -> 02 Macro -> 03 Markets
    "recover":  (11.3, 15.7),  # bento grid re-forms, red markers flip to green; statement
    "logo":     (15.7, 18.75), # V line draws, wordmark and subtitle, CTA
    "endcard":  (18.75, 21.0), # end card, fully settled from 19.0 to 21.0
}

# narration-locked events
EVENTS = {
    "slips": [0.27, 0.85, 1.47, 1.95, 2.57, 2.80, 3.05, 3.28],
    "fall": 3.55,
    "w_every": 3.75, "w_headline": 4.05, "w_moves": 4.48, "w_your": 4.72, "w_money": 4.92,
    "turn_out": 5.9,
    "slip_back": 6.15, "flip": 6.75, "expand": 7.35,
    "tile_1": 8.35, "tile_2": 9.65, "tile_3": 10.56,
    "card_out": 11.2, "grid_in": 11.15, "no_panic": 12.72, "flip_green": 12.78,
    "w_understand": 13.66, "w_world": 14.15, "w_invest": 14.8, "w_better": 15.1,
    "statement_out": 15.68,
    "vline": 15.85, "wordmark": 16.15, "subtitle": 16.75, "cta": 17.55,
    "to_endcard": 18.75, "endcard": 19.0,
}

# fast-motion windows -> extra motion-blur subsamples (t0, t1, n)
FAST = [(3.5, 4.05, 5), (6.15, 6.5, 4), (6.75, 7.4, 4), (11.2, 12.35, 4), (12.75, 13.75, 3),
        (15.55, 15.95, 4), (18.7, 19.05, 4)]

HANDLE = "@panicandprofit"

TEXT = {"en": {
    "breaking": "BREAKING", "live": "LIVE",
    "ticker": ["MARKETS", "OIL", "BONDS", "CURRENCIES", "STOCKS", "GROWTH", "TRADE"],
    "slips": [("MARKETS", "MARKETS SLIDE"), ("WORLD", "TRADE FEARS GROW"), ("ENERGY", "OIL SPIKES"),
              ("FX", "CURRENCY SLUMPS"), ("CENTRAL BANKS", "RATES UP AGAIN"), ("STOCKS", "SELL-OFF DEEPENS"),
              ("ECONOMY", "RECESSION FEARS"), ("MARKETS", "INVESTORS RUSH OUT")],
    "calm": ["MARKETS RECOVER", "TRADE TALKS RESUME", "OIL STEADIES", "CURRENCY STEADIES",
             "RATES ON HOLD", "BUYERS RETURN", "GROWTH HOLDS UP", "CALM RETURNS"],
    "turn": [("Every", 0), ("headline", 0), ("moves", 1), ("your", 1), ("money.", 1)],
    "back_kicker": "EXPLAINED", "back_title": "Behind the headline",
    "tiles": [("01", "Geopolitics", "Conflicts, trade, elections"),
              ("02", "Macro", "Inflation, rates, growth"),
              ("03", "Markets", "Stocks, bonds, your savings")],
    "statement": [("Understand", 0), ("the", 0), ("world.", 0), ("Invest", 1), ("better.", 1)],
    "subtitle": "MARKETS · MACRO · GEOPOLITICS",
    "cta": "Follow @panicandprofit",
    "end_line": "Follow for markets, macro & geopolitics",
    "end_small": "NOT FINANCIAL ADVICE",
}}
