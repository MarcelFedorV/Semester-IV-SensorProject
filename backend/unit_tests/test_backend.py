# Unit tests for core backend modules: fish data, fish logic, agent, achievements, and database.

import unittest
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class TestFishData(unittest.TestCase):

    def test_have_fish(self):
        from fish_data import FISH
        self.assertGreater(len(FISH), 0)

    def test_fish_fields(self):
        from fish_data import FISH
        for fish in FISH:
            self.assertIn('id', fish)
            self.assertIn('name', fish)
            self.assertIn('rarity', fish)

    def test_no_duplicate_ids(self):
        from fish_data import FISH, MYSTERY_FISH
        all_ids = [f['id'] for f in FISH] + [f['id'] for f in MYSTERY_FISH]
        self.assertEqual(len(all_ids), len(set(all_ids)))

    def test_locations_defined(self):
        from fish_data import LOCATIONS
        self.assertGreater(len(LOCATIONS), 0)


class TestFishLogic(unittest.TestCase):

    def test_depth_multiplier(self):
        from fish_logic import get_depth_multiplier
        result = get_depth_multiplier("Common", 0.5)
        self.assertGreater(result, 0)

    def test_pick_fish_empty_pool(self):
        from fish_logic import pick_fish
        result = pick_fish(0.5, 1, [])
        self.assertIsNone(result)

    def test_pick_fish_with_pool(self):
        from fish_logic import pick_fish
        from fish_data import FISH
        pool = [f for f in FISH if f['location_id'] == 1]
        if len(pool) > 0:
            result = pick_fish(0.5, 1, pool)
            if result:
                self.assertIn('id', result)


class TestFishAgent(unittest.TestCase):

    def test_create_agent(self):
        from fish_agent import FishAgent
        from fish_data import FISH
        agent = FishAgent(FISH[0])
        self.assertIsNotNone(agent)

    def test_agent_perceive(self):
        from fish_agent import FishAgent
        from fish_data import FISH
        agent = FishAgent(FISH[0])
        percepts = agent.perceive(0.5, 1)
        self.assertIn('depth', percepts)

    def test_agent_decide(self):
        from fish_agent import FishAgent
        from fish_data import FISH
        agent = FishAgent(FISH[0])
        decision = agent.decide({'depth': 0.5, 'location_match': True, 'habitat_match': True})
        self.assertIn(decision, ['bite', 'nibble', 'ignore'])

    def test_agent_act(self):
        from fish_agent import FishAgent
        from fish_data import FISH
        agent = FishAgent(FISH[0])
        result_bite = agent.act('bite')
        self.assertTrue(result_bite['caught'])
        result_ignore = agent.act('ignore')
        self.assertFalse(result_ignore['caught'])

    def test_full_agent_loop(self):
        from fish_agent import FishAgent
        from fish_data import FISH
        agent = FishAgent(FISH[0])
        result = agent.run(0.5, 1)
        self.assertIn('caught', result)


class TestAchievements(unittest.TestCase):

    def test_achievements_exist(self):
        from achievements import ACHIEVEMENTS
        self.assertGreater(len(ACHIEVEMENTS), 0)

    def test_achievement_structure(self):
        from achievements import ACHIEVEMENTS
        for ach in ACHIEVEMENTS:
            self.assertIn('id', ach)
            self.assertIn('name', ach)


class TestDatabase(unittest.TestCase):

    def test_database_module(self):
        try:
            from database import engine, SessionLocal, Base
            self.assertIsNotNone(engine)
        except ImportError:
            self.skipTest("SQLAlchemy not installed")


class TestModels(unittest.TestCase):

    def test_user_model(self):
        try:
            from models import User
            self.assertIsNotNone(User)
        except ImportError:
            self.skipTest("SQLAlchemy not installed")


class TestUtils(unittest.TestCase):

    def test_scripts_exist(self):
        backend_dir = os.path.dirname(os.path.dirname(__file__))
        self.assertTrue(os.path.exists(os.path.join(backend_dir, 'create_admin.py')))
        self.assertTrue(os.path.exists(os.path.join(backend_dir, 'create_user.py')))

    def test_main_exists(self):
        backend_dir = os.path.dirname(os.path.dirname(__file__))
        self.assertTrue(os.path.exists(os.path.join(backend_dir, 'main.py')))


if __name__ == "__main__":
    unittest.main(verbosity=2)
