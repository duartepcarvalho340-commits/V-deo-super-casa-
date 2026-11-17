"""Timing and on-screen text for the Panic & Profit launch reel. All times in seconds.
Times follow the narration in audio/voice_timing_en.json (ElevenLabs voice "Marcus" via Higgsfield)."""

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
    "slips": [-0.2, 0.75, 1.34, 1.85, 2.38, 2.75, 3.02, 3.28],
    "fall": 3.6,
    "w_every": 3.72, "w_headline": 4.1, "w_moves": 4.55, "w_your": 4.82, "w_money": 5.0,
    "turn_out": 5.9,
    "slip_back": 6.15, "flip": 6.75, "expand": 7.35,
    "tile_1": 8.3, "tile_2": 9.6, "tile_3": 10.5,
    "card_out": 11.2, "grid_in": 11.15, "no_panic": 12.65, "flip_green": 12.72,
    "w_understand": 13.5, "w_world": 14.2, "w_invest": 14.78, "w_better": 15.3,
    "statement_out": 15.9,
    "vline": 16.0, "wordmark": 16.3, "subtitle": 16.9, "cta": 17.7,
    "to_endcard": 18.75, "endcard": 19.0,
}

# fast-motion windows -> extra motion-blur subsamples (t0, t1, n)
FAST = [(3.55, 4.1, 5), (6.15, 6.5, 4), (6.75, 7.4, 4), (11.2, 12.35, 4), (12.75, 13.75, 3),
        (15.85, 16.2, 4), (18.7, 19.05, 4)]

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
