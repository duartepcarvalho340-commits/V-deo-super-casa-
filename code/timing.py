"""Editable timing for the SUPERCASA spec film (pop-up book concept). All times in seconds."""

FPS = 60
DURATION = 21.0

# page turns: (start, duration). The spread index advances when each turn lands.
TURNS = [(3.05, 0.75), (6.75, 0.75), (10.15, 0.75)]
COVER_OPEN = (0.35, 0.9)      # closed book -> cover swings open
BOOK_CLOSE = (14.55, 0.85)     # last spread folds shut, cover returns
END_OPEN = (18.3, 0.55)      # cover opens one last time onto the end card

EVENTS = {
    "house_pop": 1.25, "house_lights": 2.2,
    "type_start": 3.45, "type_end": 4.0, "toggle_rent": 4.35,
    "chip_1": 4.95, "chip_2": 5.2, "chip_3": 5.45, "results": 5.8,
    "pin_1": 7.45, "pin_2": 7.65, "pin_3": 7.85, "pin_4": 8.05, "pin_5": 8.25, "near_me": 8.7,
    "heart": 11.4, "bell": 12.4, "alert_1": 12.7, "alert_2": 13.5,
    "logo_gleam": 15.5, "tagline": 16.45, "card": 18.85,
}

TEXT = {
    "en": {
        "story_1": "Every home", "story_2": "starts with", "story_3": "a story.",
        "buy": "Buy", "rent": "Rent", "search_q": "Lisbon", "search_ph": "City, area or address",
        "search_h1": "Buy or rent,", "search_h2": "anywhere in", "search_h3": "Portugal.",
        "chips": ["Pool", "3 bedrooms", "Garden"], "results": "1,284 homes found",
        "near_me": "Near me", "map_h": "Explore the map",
        "listing_t": "3-bed house · Cascais", "listing_p": "€ 485,000", "listing_m": "3 bed  ·  2 bath  ·  140 m²",
        "save_h1": "Save the ones", "save_h2": "you love.",
        "alerts_h": "New homes, first.", "alert_1": ["New listing in Porto", "2 bed · matches your search"],
        "alert_2": ["Price drop in Cascais", "Saved home · now € 469,000"], "now": "now", "min": "3 min",
        "tagline": "Your next chapter starts here.",
        "disclaimer": "Independent concept · not affiliated with SUPERCASA",
    },
    "pt": {
        "story_1": "Cada casa", "story_2": "começa com", "story_3": "uma história.",
        "buy": "Comprar", "rent": "Arrendar", "search_q": "Lisboa", "search_ph": "Cidade, zona ou morada",
        "search_h1": "Comprar ou arrendar,", "search_h2": "de norte a sul", "search_h3": "do país.",
        "chips": ["Piscina", "T3", "Jardim"], "results": "1 284 casas encontradas",
        "near_me": "Perto de mim", "map_h": "Explore o mapa",
        "listing_t": "Moradia T3 · Cascais", "listing_p": "485 000 €", "listing_m": "3 quartos  ·  2 WC  ·  140 m²",
        "save_h1": "Guarde as que", "save_h2": "mais gosta.",
        "alerts_h": "Seja o primeiro a saber.", "alert_1": ["Novo anúncio no Porto", "T2 · corresponde à pesquisa"],
        "alert_2": ["Baixa de preço em Cascais", "Favorito · agora 469 000 €"], "now": "agora", "min": "3 min",
        "tagline": "O seu próximo capítulo começa aqui.",
        "disclaimer": "Conceito independente · sem afiliação à SUPERCASA",
    },
}

NAME = "Duarte Carvalho"
HANDLE = "@duartecarvalho"
AVATAR_INITIALS = "DC"
