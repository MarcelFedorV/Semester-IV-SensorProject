# Essential gameplay tests: depth-rarity system, agent behaviour, fish data integrity, and catch logic.

import unittest
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fish_logic import get_depth_multiplier, pick_fish, try_catch_fish
from fish_agent import FishAgent
from fish_data import FISH, MYSTERY_FISH_BY_LOCATION, LOCATIONS


class TestDepthSystem(unittest.TestCase):

    def test_surface_boosts_common(self):
        self.assertEqual(get_depth_multiplier("Common", 0.2), 1.5)

    def test_deep_boosts_legendary(self):
        self.assertEqual(get_depth_multiplier("Legendary", 0.8), 3.0)

    def test_pick_fish_works(self):
        pool = [{"id": 1, "name": "Test", "rarity": "Common", "location_id": 1}]
        fish = pick_fish(0.5, 1, pool)
        self.assertIsNotNone(fish)
        self.assertEqual(fish["id"], 1)


class TestFishAgent(unittest.TestCase):

    def setUp(self):
        self.fish = {"id": 1, "name": "Herring", "rarity": "Common", "location_id": 1, "depth": "mid"}
        self.agent = FishAgent(self.fish)

    def test_catches_at_correct_location_and_depth(self):
        result = self.agent.run(0.5, 1)
        self.assertTrue(result["caught"])

    def test_ignores_at_wrong_location(self):
        result = self.agent.run(0.5, 2)
        self.assertFalse(result["caught"])


class TestFishData(unittest.TestCase):

    def test_fish_have_ids(self):
        ids = [f["id"] for f in FISH]
        self.assertEqual(len(ids), len(set(ids)))

    def test_fish_have_locations(self):
        valid_locs = [loc["id"] for loc in LOCATIONS]
        for fish in FISH:
            self.assertIn(fish["location_id"], valid_locs)

    def test_mystery_fish_exist(self):
        self.assertGreater(len(MYSTERY_FISH_BY_LOCATION), 0)


class TestCatchLogic(unittest.TestCase):

    def test_catch_correct_location(self):
        fish = {"id": 1, "name": "Test", "location_id": 1, "depth": "mid"}
        result = try_catch_fish(fish, 0.5, 1)
        self.assertTrue(result["caught"])

    def test_miss_wrong_location(self):
        fish = {"id": 1, "name": "Test", "location_id": 1, "depth": "mid"}
        result = try_catch_fish(fish, 0.5, 2)
        self.assertFalse(result["caught"])


if __name__ == '__main__':
    unittest.main(verbosity=2)