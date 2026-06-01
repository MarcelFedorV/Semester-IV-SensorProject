# Unit tests for core backend modules: sensor device, fish data, fish logic, agent, achievements, and database.

import unittest
import sys
import os
import importlib.util
from unittest.mock import patch

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
SENSOR_DEVICE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'sensor_device'))


class TestSensorConstants(unittest.TestCase):

    def test_uuids_exist(self):
        spec = importlib.util.spec_from_file_location(
            "constants",
            os.path.join(SENSOR_DEVICE_DIR, 'constants.py')
        )
        constants = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(constants)
        self.assertIsInstance(constants.CSC_SERVICE, str)
        self.assertIsInstance(constants.CSC_MEASUREMENT, str)

    def test_locations_mapping(self):
        spec = importlib.util.spec_from_file_location(
            "constants",
            os.path.join(SENSOR_DEVICE_DIR, 'constants.py')
        )
        constants = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(constants)
        self.assertIsInstance(constants.CSC_LOCATIONS, dict)
        self.assertEqual(constants.CSC_LOCATIONS[0], "Other")
        self.assertEqual(constants.CSC_LOCATIONS[12], "Rear Wheel")


class TestSensorModels(unittest.TestCase):

    def test_device_info_basic(self):
        spec = importlib.util.spec_from_file_location(
            "models",
            os.path.join(SENSOR_DEVICE_DIR, 'models.py')
        )
        models = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(models)
        device = models.DeviceInfo(
            address="AA:BB:CC:DD:EE:FF",
            name="Test Sensor",
            rssi=-50,
            last_seen="2024-01-01",
            connectable=True
        )
        self.assertEqual(device.address, "AA:BB:CC:DD:EE:FF")
        self.assertEqual(device.name, "Test Sensor")
        self.assertEqual(device.rssi, -50)

    def test_device_display_name(self):
        spec = importlib.util.spec_from_file_location(
            "models",
            os.path.join(SENSOR_DEVICE_DIR, 'models.py')
        )
        models = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(models)
        device1 = models.DeviceInfo(address="AA:BB:CC:DD:EE:FF", name="My Sensor", rssi=-50, last_seen="now", connectable=True)
        self.assertEqual(device1.display_name, "My Sensor")
        device2 = models.DeviceInfo(address="AA:BB:CC:DD:EE:FF", name="", rssi=-50, last_seen="now", connectable=True)
        self.assertIn("AA:BB:CC:DD:EE:FF", device2.display_name)


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

    def test_depth_multiplier_boundary_surface(self):
        from fish_logic import get_depth_multiplier
        # Surface depth (0.0) should boost common fish
        result_common = get_depth_multiplier("Common", 0.0)
        self.assertGreater(result_common, 1.0)  # should have surface boost

    def test_depth_multiplier_boundary_deep(self):
        from fish_logic import get_depth_multiplier
        # Deep depth (1.0) should boost legendary fish
        result_legendary = get_depth_multiplier("Legendary", 1.0)
        self.assertGreater(result_legendary, 2.0)  # should have deep boost

    def test_depth_multiplier_unknown_rarity(self):
        from fish_logic import get_depth_multiplier
        # Unknown rarity should still return positive multiplier
        result = get_depth_multiplier("UnknownRarity", 0.5)
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

    def test_pick_fish_deterministic(self):
        from fish_logic import pick_fish
        from unittest.mock import patch
        pool = [{"id": 1, "name": "Test", "rarity": "Common", "location_id": 1}]
        # Mock random.random to always return 0.1 (should pick first fish)
        with patch('random.random', return_value=0.1):
            result = pick_fish(0.5, 1, pool)
            self.assertIsNotNone(result)
            self.assertEqual(result["id"], 1)


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

    def test_achievement_fields_complete(self):
        from achievements import ACHIEVEMENTS
        # Validate all achievements have required fields and no empty values
        for ach in ACHIEVEMENTS:
            self.assertIsNotNone(ach.get('id'))
            self.assertIsNotNone(ach.get('name'))
            self.assertTrue(len(str(ach.get('name', ''))) > 0)

    def test_achievement_ids_unique(self):
        from achievements import ACHIEVEMENTS
        ids = [a['id'] for a in ACHIEVEMENTS]
        self.assertEqual(len(ids), len(set(ids)))


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