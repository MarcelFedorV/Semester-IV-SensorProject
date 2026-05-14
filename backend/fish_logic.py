import random
from fish_data import FISH
from fish_agent import FishAgent

# Base rarity weights
BASE_RARITY_WEIGHTS = {
    "Common":          100,
    "Uncommon":        40,
    "Rare":            15,
    "Legendary":       5,
    "Location Legend": 30,
}

def get_depth_multiplier(rarity: str, depth: float) -> float:
    """
    Returns multiplier for rarity based on depth.
    Deeper water = better chance for rare fish.
    
    Args:
        rarity: Fish rarity (Common, Uncommon, Rare, Legendary)
        depth: Fishing depth (0.0 = surface, 1.0 = deepest)
    
    Returns:
        Multiplier to apply to base rarity weight
    """
    if depth < 0.35:  # Surface
        multipliers = {
            "Common": 1.5,      # 150% - Common very common
            "Uncommon": 0.8,    # 80% - Uncommon slightly reduced
            "Rare": 0.3,        # 30% - Rare very rare
            "Legendary": 0.1,   # 10% - Legendary almost impossible
            "Location Legend": 0.5,
        }
    elif depth < 0.7:  # Mid depth
        multipliers = {
            "Common": 1.0,      # 100% - Normal rates
            "Uncommon": 1.0,    # 100%
            "Rare": 1.0,        # 100%
            "Legendary": 0.5,   # 50% - Still harder
            "Location Legend": 1.0,
        }
    else:  # Deep (0.7+)
        multipliers = {
            "Common": 0.6,      # 60% - Common reduced
            "Uncommon": 1.2,    # 120% - Uncommon boosted
            "Rare": 2.0,        # 200% - Rare doubled!
            "Legendary": 3.0,   # 300% - Legendary tripled!
            "Location Legend": 2.0,
        }
    return multipliers.get(rarity, 1.0)

def pick_fish(depth: float, location_id: int, pool: list) -> dict:
    """
    Pick a fish from the pool based on rarity weights and depth.
    
    Args:
        depth: Fishing depth (0.0-1.0)
        location_id: Location ID
        pool: List of fish to choose from
    
    Returns:
        Selected fish dictionary, or None if pool is empty
    """
    if not pool:
        return None
    
    # Build weighted pool - each fish gets weight based on rarity AND depth
    weighted_pool = []
    weights = []
    
    for fish in pool:
        rarity = fish.get("rarity", "Common")
        base_weight = BASE_RARITY_WEIGHTS.get(rarity, 50)
        depth_multiplier = get_depth_multiplier(rarity, depth)
        final_weight = base_weight * depth_multiplier
        
        weighted_pool.append(fish)
        weights.append(final_weight)
    
    # Pick a fish based on weighted probabilities
    selected_fish = random.choices(weighted_pool, weights=weights, k=1)[0]
    return selected_fish

def try_catch_fish(fish: dict, depth: float, location_id: int) -> dict:
    """
    Try to catch a specific fish using FishAgent.
    
    Args:
        fish: Fish dictionary to try catching
        depth: Fishing depth
        location_id: Location ID
    
    Returns:
        Agent result with caught status
    """
    agent = FishAgent(fish)
    result = agent.run(depth, location_id)
    return result