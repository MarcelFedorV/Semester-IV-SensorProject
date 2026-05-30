import random
from fish_agent import FishAgent


BASE_RARITY_WEIGHTS = {
    "Common":          100,
    "Uncommon":        40,
    "Rare":            15,
    "Legendary":       5,
    "Location Legend": 30,
}

def get_depth_multiplier(rarity: str, depth: float) -> float:
    if depth < 0.35:  # Surface
        multipliers = {
            "Common": 1.5,      # 150% 
            "Uncommon": 0.8,    # 80% 
            "Rare": 0.3,        # 30% 
            "Legendary": 0.1,   # 10% 
            "Location Legend": 0.5,
        }
    elif depth < 0.7:  # Mid depth
        multipliers = {
            "Common": 1.0,      # 100% 
            "Uncommon": 1.0,    # 100%
            "Rare": 1.0,        # 100%
            "Legendary": 0.5,   # 50% 
            "Location Legend": 1.0,
        }
    else:  # Deep (0.7+)
        multipliers = {
            "Common": 0.6,      # 60% 
            "Uncommon": 1.2,    # 120% 
            "Rare": 2.0,        # 200% 
            "Legendary": 3.0,   # 300% 
            "Location Legend": 2.0,
        }
    return multipliers.get(rarity, 1.0)

def pick_fish(depth: float, location_id: int, pool: list) -> dict:
   
    if not pool:
        return None
    
   
    weighted_pool = []
    weights = []
    
    for fish in pool:
        rarity = fish.get("rarity", "Common")
        base_weight = BASE_RARITY_WEIGHTS.get(rarity, 50)
        depth_multiplier = get_depth_multiplier(rarity, depth)
        final_weight = base_weight * depth_multiplier
        
        weighted_pool.append(fish)
        weights.append(final_weight)
    
    selected_fish = random.choices(weighted_pool, weights=weights, k=1)[0]
    return selected_fish

def try_catch_fish(fish: dict, depth: float, location_id: int) -> dict:
    agent = FishAgent(fish)
    result = agent.run(depth, location_id)
    return result