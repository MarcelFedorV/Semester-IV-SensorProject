"""
Essential Unit Tests for Fishing Game Backend
Tests the most critical functionality with minimal overhead
"""
import unittest
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fish_logic import get_depth_multiplier, pick_fish, try_catch_fish
from fish_agent import FishAgent
from fish_data import FISH, MYSTERY_FISH_BY_LOCATION, LOCATIONS


class TestDepthSystem(unittest.TestCase):
    """Test depth-based rarity mechanics"""
    
    def test_surface_boosts_common(self):
        """Common fish get 150% at surface"""
        self.assertEqual(get_depth_multiplier("Common", 0.2), 1.5)
    
    def test_deep_boosts_legendary(self):
        """Legendary fish get 300% in deep water"""
        self.assertEqual(get_depth_multiplier("Legendary", 0.8), 3.0)
    
    def test_pick_fish_works(self):
        """Fish selection returns valid fish"""
        pool = [{"id": 1, "name": "Test", "rarity": "Common", "location_id": 1}]
        fish = pick_fish(0.5, 1, pool)
        self.assertIsNotNone(fish)
        self.assertEqual(fish["id"], 1)


class TestFishAgent(unittest.TestCase):
    """Test reactive agent behavior"""
    
    def setUp(self):
        self.fish = {"id": 1, "name": "Herring", "rarity": "Common", "location_id": 1}
        self.agent = FishAgent(self.fish)
    
    def test_catches_at_correct_location(self):
        """Agent catches fish at correct location"""
        result = self.agent.run(0.5, 1)
        self.assertTrue(result["caught"])
    
    def test_ignores_at_wrong_location(self):
        """Agent ignores fish at wrong location"""
        result = self.agent.run(0.5, 2)
        self.assertFalse(result["caught"])


class TestFishData(unittest.TestCase):
    """Test fish data integrity"""
    
    def test_fish_have_ids(self):
        """All fish have unique IDs"""
        ids = [f["id"] for f in FISH]
        self.assertEqual(len(ids), len(set(ids)))
    
    def test_fish_have_locations(self):
        """All fish have valid locations"""
        valid_locs = [loc["id"] for loc in LOCATIONS]
        for fish in FISH:
            self.assertIn(fish["location_id"], valid_locs)
    
    def test_mystery_fish_exist(self):
        """Mystery fish are configured"""
        self.assertGreater(len(MYSTERY_FISH_BY_LOCATION), 0)


class TestCatchLogic(unittest.TestCase):
    """Test fish catching logic"""
    
    def test_catch_correct_location(self):
        """Fish caught at matching location"""
        fish = {"id": 1, "name": "Test", "location_id": 1}
        result = try_catch_fish(fish, 0.5, 1)
        self.assertTrue(result["caught"])
    
    def test_miss_wrong_location(self):
        """Fish missed at wrong location"""
        fish = {"id": 1, "name": "Test", "location_id": 1}
        result = try_catch_fish(fish, 0.5, 2)
        self.assertFalse(result["caught"])


if __name__ == '__main__':
    # Run with summary
    loader = unittest.TestLoader()
    suite = loader.loadTestsFromModule(sys.modules[__name__])
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    print("\n" + "="*50)
    print(f"✅ Tests Passed: {result.testsRun - len(result.failures) - len(result.errors)}/{result.testsRun}")
    print("="*50)
