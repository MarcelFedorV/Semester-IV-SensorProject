from fish_data import FISH_BY_RARITY, FISH, LOCATIONS, LOCATIONS_BY_ID
import random

RARITY_WEIGHTS_BY_DEPTH = {
    "surface": {"Common": 100, "Uncommon": 0,  "Rare": 0,  "Legendary": 0},
    "mid":     {"Common": 60,  "Uncommon": 35, "Rare": 5,  "Legendary": 0},
    "deep":    {"Common": 20,  "Uncommon": 40, "Rare": 30, "Legendary": 10},
}

def depth_to_zone(depth: float) -> str:
    if depth < 0.35:
        return "surface"
    elif depth < 0.7:
        return "mid"
    else:
        return "deep"

def pick_rarity(zone: str) -> str:
    weights = RARITY_WEIGHTS_BY_DEPTH[zone]
    rarities = list(weights.keys())
    values   = list(weights.values())
    return random.choices(rarities, weights=values, k=1)[0]

def pick_fish(depth: float, location_id: int = 1) -> dict:
    zone   = depth_to_zone(depth)
    rarity = pick_rarity(zone)

    # Filter fish by location and rarity
    zone_order = ["surface", "mid", "deep"]
    max_index  = zone_order.index(zone)

    pool = [
        f for f in FISH
        if f["rarity"] == rarity
        and f["location_id"] == location_id
        and zone_order.index(f["depth"]) <= max_index
    ]

    # Fallback — ignore location if no fish found
    if not pool:
        pool = [f for f in FISH if f["rarity"] == rarity]

    # Final fallback
    if not pool:
        pool = FISH

    return random.choice(pool)