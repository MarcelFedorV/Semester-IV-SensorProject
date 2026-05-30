# achievements.py

ACHIEVEMENTS = [
    # ── Fishing achievements ──────────────────────────────
    {
        "id":          "first_catch",
        "name":        "First Catch!",
        "description": "Catch your first fish",
        "icon":        "*",
        "category":    "fishing",
    },
    {
        "id":          "deep_diver",
        "name":        "Deep Diver",
        "description": "Reach maximum depth",
        "icon":        "~",
        "category":    "fishing",
    },
    {
        "id":          "lucky_day",
        "name":        "Lucky Day",
        "description": "Catch a Legendary fish",
        "icon":        "!",
        "category":    "fishing",
    },
    {
        "id":          "collector_10",
        "name":        "Budding Collector",
        "description": "Catch 10 different fish",
        "icon":        "10",
        "category":    "fishing",
    },
    {
        "id":          "collector_25",
        "name":        "Serious Collector",
        "description": "Catch 25 different fish",
        "icon":        "25",
        "category":    "fishing",
    },
    {
        "id":          "collector_all",
        "name":        "Master Angler",
        "description": "Catch every fish in the game",
        "icon":        "ALL",
        "category":    "fishing",
    },
    {
        "id":          "baltic_master",
        "name":        "Baltic Master",
        "description": "Catch all fish in the Baltic Sea",
        "icon":        "X",
        "category":    "fishing",
    },
    {
        "id":          "north_master",
        "name":        "North Sea Master",
        "description": "Catch all fish in the North Sea",
        "icon":        "X",
        "category":    "fishing",
    },
    {
        "id":          "caribbean_master",
        "name":        "Caribbean Master",
        "description": "Catch all fish in the Caribbean",
        "icon":        "X",
        "category":    "fishing",
    },
    {
        "id":          "pacific_master",
        "name":        "Pacific Master",
        "description": "Catch all fish in the Pacific Ocean",
        "icon":        "X",
        "category":    "fishing",
    },
    {
        "id":          "trench_master",
        "name":        "Trench Master",
        "description": "Catch all fish in the Mariana Trench",
        "icon":        "X",
        "category":    "fishing",
    },
    {
        "id":          "mystery_first",
        "name":        "What Was That?!",
        "description": "Catch your first Location Legend fish",
        "icon":        "?",
        "category":    "fishing",
    },

    # ── Distance achievements ─────────────────────────────
    {
        "id":          "distance_first",
        "name":        "First Pedal",
        "description": "Pedal your first 100 meters",
        "icon":        "1",
        "category":    "distance",
        "threshold_m": 100,
    },
    {
        "id":          "distance_1km",
        "name":        "Warming Up",
        "description": "Pedal 1 km total",
        "icon":        "1k",
        "category":    "distance",
        "threshold_m": 1000,
    },
    {
        "id":          "distance_5km",
        "name":        "Getting Somewhere",
        "description": "Pedal 5 km total",
        "icon":        "5k",
        "category":    "distance",
        "threshold_m": 5000,
    },
    {
        "id":          "distance_10km",
        "name":        "Going Places",
        "description": "Pedal 10 km total",
        "icon":        "10k",
        "category":    "distance",
        "threshold_m": 10000,
    },
    {
        "id":          "distance_25km",
        "name":        "Road Warrior",
        "description": "Pedal 25 km total",
        "icon":        "25k",
        "category":    "distance",
        "threshold_m": 25000,
    },
    {
        "id":          "distance_50km",
        "name":        "Iron Legs",
        "description": "Pedal 50 km total",
        "icon":        "50k",
        "category":    "distance",
        "threshold_m": 50000,
    },
    {
        "id":          "distance_100km",
        "name":        "Century Rider",
        "description": "Pedal 100 km total",
        "icon":        "100k",
        "category":    "distance",
        "threshold_m": 100000,
    },
]

ACHIEVEMENTS_BY_ID = {a["id"]: a for a in ACHIEVEMENTS}
DISTANCE_ACHIEVEMENTS = [a for a in ACHIEVEMENTS if a["category"] == "distance"]
FISHING_ACHIEVEMENTS  = [a for a in ACHIEVEMENTS if a["category"] == "fishing"]