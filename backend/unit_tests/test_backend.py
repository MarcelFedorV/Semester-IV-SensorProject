"""
Backend Unit Tests
Testing core functionality of the backend modules
"""
import unittest
import sys
import os
import importlib.util

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


# Sensor device tests
class TestSensorConstants(unittest.TestCase):
    
    def test_uuids_exist(self):
        # Load constants without importing the whole package
        spec = importlib.util.spec_from_file_location(
            "constants",
            os.path.join(os.path.dirname(__file__), '..', 'sensor_device', 'constants.py')
        )
        constants = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(constants)
        
        # Check UUIDs are strings
        self.assertIsInstance(constants.CSC_SERVICE, str)
        self.assertIsInstance(constants.CSC_MEASUREMENT, str)
    
    def test_locations_mapping(self):
        spec = importlib.util.spec_from_file_location(
            "constants",
            os.path.join(os.path.dirname(__file__), '..', 'sensor_device', 'constants.py')
        )
        constants = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(constants)
        
        # Make sure we have location names
        self.assertIsInstance(constants.CSC_LOCATIONS, dict)
        self.assertEqual(constants.CSC_LOCATIONS[0], "Other")
        self.assertEqual(constants.CSC_LOCATIONS[12], "Rear Wheel")


class TestSensorModels(unittest.TestCase):
    
    def test_device_info_basic(self):
        spec = importlib.util.spec_from_file_location(
            "models",
            os.path.join(os.path.dirname(__file__), '..', 'sensor_device', 'models.py')
        )
        models = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(models)
        
        # Try creating a device
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
            os.path.join(os.path.dirname(__file__), '..', 'sensor_device', 'models.py')
        )
        models = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(models)
        
        # With name
        device1 = models.DeviceInfo(
            address="AA:BB:CC:DD:EE:FF",
            name="My Sensor",
            rssi=-50,
            last_seen="now",
            connectable=True
        )
        self.assertEqual(device1.display_name, "My Sensor")
        
        # Without name - should show address
        device2 = models.DeviceInfo(
            address="AA:BB:CC:DD:EE:FF",
            name="",
            rssi=-50,
            last_seen="now",
            connectable=True
        )
        self.assertIn("AA:BB:CC:DD:EE:FF", device2.display_name)


# Fish data tests
class TestFishData(unittest.TestCase):
    
    def test_have_fish(self):
        from fish_data import FISH
        # Should have some fish
        self.assertGreater(len(FISH), 0)
    
    def test_fish_fields(self):
        from fish_data import FISH
        # Every fish needs id and name
        for fish in FISH:
            self.assertIn('id', fish)
            self.assertIn('name', fish)
            self.assertIn('rarity', fish)
    
    def test_no_duplicate_ids(self):
        from fish_data import FISH, MYSTERY_FISH
        all_ids = [f['id'] for f in FISH] + [f['id'] for f in MYSTERY_FISH]
        # No duplicates
        self.assertEqual(len(all_ids), len(set(all_ids)))
    
    def test_locations_defined(self):
        from fish_data import LOCATIONS
        self.assertGreater(len(LOCATIONS), 0)


# Fish catching logic tests
class TestFishLogic(unittest.TestCase):
    
    def test_depth_multiplier(self):
        from fish_logic import get_depth_multiplier
        # Should return a positive number
        result = get_depth_multiplier("Common", 0.5)
        self.assertGreater(result, 0)
    
    def test_pick_fish_empty_pool(self):
        from fish_logic import pick_fish
        # Empty pool should return None
        result = pick_fish(0.5, 1, [])
        self.assertIsNone(result)
    
    def test_pick_fish_with_pool(self):
        from fish_logic import pick_fish
        from fish_data import FISH
        # Get some fish for location 1
        pool = [f for f in FISH if f['location_id'] == 1]
        if len(pool) > 0:
            result = pick_fish(0.5, 1, pool)
            # Should either return a fish or None
            if result:
                self.assertIn('id', result)


# Fish agent tests (reactive AI)
class TestFishAgent(unittest.TestCase):
    
    def test_create_agent(self):
        from fish_agent import FishAgent
        from fish_data import FISH
        # Should be able to create an agent
        agent = FishAgent(FISH[0])
        self.assertIsNotNone(agent)
    
    def test_agent_perceive(self):
        from fish_agent import FishAgent
        from fish_data import FISH
        agent = FishAgent(FISH[0])
        # Agent should perceive environment
        percepts = agent.perceive(0.5, 1)
        self.assertIn('depth', percepts)
    
    def test_agent_decide(self):
        from fish_agent import FishAgent
        from fish_data import FISH
        agent = FishAgent(FISH[0])
        # Agent should make a decision
        decision = agent.decide({'depth': 0.5, 'location_match': True})
        self.assertIn(decision, ['bite', 'ignore'])
    
    def test_agent_act(self):
        from fish_agent import FishAgent
        from fish_data import FISH
        agent = FishAgent(FISH[0])
        # Test both actions
        result_bite = agent.act('bite')
        self.assertTrue(result_bite['caught'])
        
        result_ignore = agent.act('ignore')
        self.assertFalse(result_ignore['caught'])
    
    def test_full_agent_loop(self):
        from fish_agent import FishAgent
        from fish_data import FISH
        agent = FishAgent(FISH[0])
        # Run the full loop
        result = agent.run(0.5, 1)
        self.assertIn('caught', result)


# Achievement tests
class TestAchievements(unittest.TestCase):
    
    def test_achievements_exist(self):
        from achievements import ACHIEVEMENTS
        self.assertGreater(len(ACHIEVEMENTS), 0)
    
    def test_achievement_structure(self):
        from achievements import ACHIEVEMENTS
        # Each achievement needs id and name
        for ach in ACHIEVEMENTS:
            self.assertIn('id', ach)
            self.assertIn('name', ach)


# Database tests (skip if SQLAlchemy not installed)
class TestDatabase(unittest.TestCase):
    
    def test_database_module(self):
        try:
            from database import engine, SessionLocal, Base
            self.assertIsNotNone(engine)
        except ImportError:
            self.skipTest("SQLAlchemy not installed")


# Models tests
class TestModels(unittest.TestCase):
    
    def test_user_model(self):
        try:
            from models import User
            self.assertIsNotNone(User)
        except ImportError:
            self.skipTest("SQLAlchemy not installed")


# Utility tests
class TestUtils(unittest.TestCase):
    
    def test_scripts_exist(self):
        # Make sure utility scripts are there
        import os
        backend_dir = os.path.dirname(os.path.dirname(__file__))
        self.assertTrue(os.path.exists(os.path.join(backend_dir, 'create_admin.py')))
        self.assertTrue(os.path.exists(os.path.join(backend_dir, 'create_user.py')))
    
    def test_main_exists(self):
        import os
        backend_dir = os.path.dirname(os.path.dirname(__file__))
        self.assertTrue(os.path.exists(os.path.join(backend_dir, 'main.py')))


if __name__ == "__main__":
    unittest.main(verbosity=2)