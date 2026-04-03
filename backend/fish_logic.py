# fishing_engine.py
import random
from fish_data import FISH_BY_RARITY

# Rarity weights based on depth (0.0 = surface, 1.0 = deep)
# At surface only Common possible, deep unlocks Rare/Legendary
RARITY_WEIGHTS_BY_DEPTH = {
    "surface": {"Common": 100, "Uncommon": 0,  "Rare": 0,  "Legendary": 0},
    "mid":     {"Common": 60,  "Uncommon": 35, "Rare": 5,  "Legendary": 0},
    "deep":    {"Common": 20,  "Uncommon": 40, "Rare": 30, "Legendary": 10},
}

def depth_to_zone(depth: float) -> str:
    """Convert 0.0-1.0 depth float to zone name."""
    if depth < 0.35:
        return "surface"
    elif depth < 0.7:
        return "mid"
    else:
        return "deep"

def pick_rarity(zone: str) -> str:
    """Pick a rarity tier based on zone weights."""
    weights = RARITY_WEIGHTS_BY_DEPTH[zone]
    rarities = list(weights.keys())
    values   = list(weights.values())
    return random.choices(rarities, weights=values, k=1)[0]

def pick_fish(depth: float) -> dict:
    """
    Main function — given a depth (0.0-1.0), returns a fish dict.
    Only picks fish whose depth zone matches or is shallower.
    """
    zone    = depth_to_zone(depth)
    rarity  = pick_rarity(zone)
    pool    = FISH_BY_RARITY[rarity]

    # Filter to fish available at this zone
    zone_order = ["surface", "mid", "deep"]
    max_index  = zone_order.index(zone)
    available  = [f for f in pool if zone_order.index(f["depth"]) <= max_index]

    # Fallback to full rarity pool if filter leaves nothing
    if not available:
        available = pool

    return random.choice(available)