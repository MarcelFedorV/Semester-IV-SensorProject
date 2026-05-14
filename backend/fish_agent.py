import random

class FishAgent:
    """
    A reactive agent representing a fish in the water.
    
    Agent loop: perceive environment → decide action → act
    
    Percepts:  depth, location_id, habitat of fish
    Actions:   ignore, nibble, bite
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
        location_match = (self.fish.get("location_id") == location_id)

        return {
            "depth":         depth,
            "location_match": location_match,
        }

    def decide(self, percepts: dict) -> str:
        """
        Rules-based decision from percepts.
        
        Actions:
          ignore  — fish not at this location
          bite    — fish goes for the bait
        """
        # Only check location - all fish can be caught at any depth
        if not percepts["location_match"]:
            return "ignore"
        
        # If location matches, fish will bite
        return "bite"

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