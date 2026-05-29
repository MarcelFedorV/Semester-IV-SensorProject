class FishAgent:
    

    HABITAT_RANGES = {
        "surface": (0.0,  0.35),
        "mid":     (0.35, 0.7),
        "deep":    (0.7,  1.0),
    }

    def __init__(self, fish: dict):
        self.fish    = fish
        self.rarity  = fish.get("rarity", "Common")
        self.habitat = fish.get("depth", "mid")

    def perceive(self, depth: float, location_id: int) -> dict:
        
        location_match = (self.fish.get("location_id") == location_id)

        low, high = self.HABITAT_RANGES.get(self.habitat, (0.0, 1.0))
        habitat_match = low <= depth < high

        return {
            "depth":          depth,
            "location_match": location_match,
            "habitat_match":  habitat_match,
        }

    def decide(self, percepts: dict) -> str:
        if not percepts["location_match"]:
            return "ignore"

        if not percepts["habitat_match"]:
            return "nibble" 

        return "bite"

    def act(self, decision: str) -> dict:
        import random
        if decision == "bite":
            caught = True
        elif decision == "nibble":
            caught = random.random() < 0.75
        else:
            caught = False

        return {
            "action": decision,
            "caught": caught,
            "fish":   self.fish if caught else None,
        }

    def run(self, depth: float, location_id: int) -> dict:
        """
        Full agent loop: perceive → decide → act
        """
        percepts = self.perceive(depth, location_id)
        decision = self.decide(percepts)
        result   = self.act(decision)
        result["percepts"] = percepts
        return result