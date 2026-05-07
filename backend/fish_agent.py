import random

class FishAgent:
    """
    A reactive agent representing a fish in the water.
    
    Agent loop: perceive environment → decide action → act
    
    Percepts:  depth, location_id, rarity of fish
    Actions:   ignore, nibble, bite, flee
    """

    def __init__(self, fish: dict):
        self.fish    = fish
        self.rarity  = fish.get("rarity", "Common")
        self.habitat = fish.get("depth", "surface")

    def perceive(self, depth: float, location_id: int) -> dict:
        """
        Gather percepts from the environment.
        Returns a percept dictionary the agent uses to decide.
        """
        # Is the bait in this fish's preferred habitat?
        if depth < 0.35:
            bait_zone = "surface"
        elif depth < 0.7:
            bait_zone = "mid"
        else:
            bait_zone = "deep"

        habitat_match = (bait_zone == self.habitat)
        location_match = (self.fish.get("location_id") == location_id)

        # Rarity affects how cautious the fish is
        caution = {
            "Common":    0.1,
            "Uncommon":  0.3,
            "Rare":      0.5,
            "Legendary": 0.75,
        }.get(self.rarity, 0.2)

        return {
            "depth":         depth,
            "bait_zone":     bait_zone,
            "habitat_match": habitat_match,
            "location_match": location_match,
            "caution":       caution,
        }

    def decide(self, percepts: dict) -> str:
        """
        Rules-based decision from percepts.
        
        Actions:
          ignore  — fish not interested
          nibble  — fish is curious, might bite
          bite    — fish goes for the bait
          flee    — fish is spooked
        """
        if not percepts["location_match"]:
            return "ignore"

        if not percepts["habitat_match"]:
            # Small chance fish wanders out of habitat
            if random.random() > 0.85:
                return "nibble"
            return "ignore"

        # Roll against caution level
        roll = random.random()

        if percepts["habitat_match"] and percepts["location_match"]:
            if roll < percepts["caution"]:
                return "flee"
            elif roll < percepts["caution"] + 0.3:
                return "nibble"
            else:
                return "bite"

        return "ignore"

    def act(self, decision: str) -> dict:
        """
        Execute the decision and return result.
        """
        return {
            "action":  decision,
            "caught":  decision == "bite",
            "fish":    self.fish if decision == "bite" else None,
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