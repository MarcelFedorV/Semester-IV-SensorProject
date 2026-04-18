

FISH = [
    #  Common 
    {
        "id": 1,
        "name": "Codfish",
        "rarity": "Common",
        "depth": "surface",
        "fact": "One of the most common fish in northern waters.",
        "color": "#7BC67E",
        "sprite": "codfish.png",
        "location_id": 1,
    },
    {
        "id": 2,
        "name": "Herring",
        "rarity": "Common",
        "depth": "surface",
        "fact": "Travels in massive schools of thousands.",
        "color": "#89CFF0",
        "sprite": "Herring.png",
        "location_id": 1,
    },
    {
        "id": 3,
        "name": "Perch",
        "rarity": "Common",
        "depth": "mid",
        "fact": "Recognizable by its striped pattern.",
        "color": "#F4A460",
        "sprite": "perch.png",
        "location_id": 1,
    },
    {
        "id": 4,
        "name": "Carp",
        "rarity": "Common",
        "depth": "mid",
        "fact": "Can live for over 20 years.",
        "color": "#DAA520",
        "sprite": "carp.png",
        "location_id": 1,
    },

    #  Uncommon 
    {
        "id": 5,
        "name": "Salmon",
        "rarity": "Uncommon",
        "depth": "mid",
        "fact": "Swims upstream to spawn where it was born.",
        "color": "#FA8072",
        "sprite": "salmon.png",
        "location_id": 1,
    },
    {
        "id": 6,
        "name": "Pike",
        "rarity": "Uncommon",
        "depth": "mid",
        "fact": "An aggressive predator with razor sharp teeth.",
        "color": "#6B8E23",
        "sprite": "dragonfish.png",
        "location_id": 1,
    },
    {
        "id": 7,
        "name": "Catfish",
        "rarity": "Uncommon",
        "depth": "deep",
        "fact": "Uses its whisker-like barbels to find food.",
        "color": "#808080",
        "sprite": "dragonfish.png",
        "location_id": 1,
    },

    # Rare 
    {
        "id": 8,
        "name": "Swordfish",
        "rarity": "Rare",
        "depth": "deep",
        "fact": "Can swim at speeds of up to 97 km/h.",
        "color": "#4169E1",
        "sprite": "swordfish.png",
        "location_id": 1,
    },
    {
        "id": 9,
        "name": "Oarfish",
        "rarity": "Rare",
        "depth": "deep",
        "fact": "The world's longest bony fish, up to 11 meters.",
        "color": "#C0C0C0",
        "sprite": "dragonfish.png",
        "location_id": 1,
    },

    #  Legendary 
    {
        "id": 10,
        "name": "Dragonfish",
        "rarity": "Legendary",
        "depth": "deep",
        "fact": "A deep sea predator.",
        "color": "#FF4500",
        "sprite": "Mythical.png",
        "location_id": 1,
    },
    {
        "id": 11,
        "name": "Golden Koi",
        "rarity": "Legendary",
        "depth": "deep",
        "fact": "Said to bring good luck to whoever catches one.",
        "color": "#FFD700",
        "sprite": "dragonfish.png",
        "location_id": 1,
    },
    {
        "id": 12,
        "name": "Alami Fish",
        "rarity": "Common",
        "depth": "surface",
        "fact": "This game is bad, why is it bad?.",
        "color": "#7BC67E",
        "sprite": "AlamiFish.png",
        "location_id": 1,
    },
]



# Quick lookup by id
FISH_BY_ID = {f["id"]: f for f in FISH}

# Mystery fish — one per location
MYSTERY_FISH = [
    {
        "id": 101,
        "name": "Baltic Ghost",
        "location_id": 1,
        "rarity": "Location Legend",
        "depth": "deep",
        "fact": "A ghostly creature said to haunt the Baltic Sea.",
        "color": "#A0C4FF",
        "sprite": None,  # add later
    },
    {
        "id": 102,
        "name": "North Sea Titan",
        "location_id": 2,
        "rarity": "Location Legend",
        "depth": "deep",
        "fact": "A massive beast lurking in the depths of the North Sea.",
        "color": "#6B8CFF",
        "sprite": None,
    },
    {
        "id": 103,
        "name": "Caribbean Phantom",
        "location_id": 3,
        "rarity": "Location Legend",
        "depth": "deep",
        "fact": "Spotted only once, by a sailor who never spoke again.",
        "color": "#FF6B6B",
        "sprite": None,
    },
    {
        "id": 104,
        "name": "Pacific Leviathan",
        "location_id": 4,
        "rarity": "Location Legend",
        "depth": "deep",
        "fact": "So large it creates its own weather patterns.",
        "color": "#4ECDC4",
        "sprite": None,
    },
    {
        "id": 105,
        "name": "Trench God",
        "location_id": 5,
        "rarity": "Location Legend",
        "depth": "deep",
        "fact": "No one has seen it and lived to tell the tale.",
        "color": "#9B59B6",
        "sprite": None,
    },
]

MYSTERY_FISH_BY_LOCATION = {f["location_id"]: f for f in MYSTERY_FISH}

# Grouped by rarity
FISH_BY_RARITY = {
    "Common":    [f for f in FISH if f["rarity"] == "Common"],
    "Uncommon":  [f for f in FISH if f["rarity"] == "Uncommon"],
    "Rare":      [f for f in FISH if f["rarity"] == "Rare"],
    "Legendary": [f for f in FISH if f["rarity"] == "Legendary"],
}

LOCATIONS = [
    {
        "id":         1,
        "name":       "Baltic Sea",
        "unlock_at":  0,
        "water_top":  [0.10, 0.30, 0.25],
        "water_deep": [0.03, 0.12, 0.10],
    },
    {
        "id":         2,
        "name":       "North Sea",
        "unlock_at":  4,
        "water_top":  [0.08, 0.18, 0.35],
        "water_deep": [0.02, 0.08, 0.18],
    },
    {
        "id":         3,
        "name":       "Caribbean",
        "unlock_at":  8,
        "water_top":  [0.05, 0.45, 0.55],
        "water_deep": [0.02, 0.20, 0.35],
    },
    {
        "id":         4,
        "name":       "Pacific Ocean",
        "unlock_at":  14,
        "water_top":  [0.03, 0.12, 0.45],
        "water_deep": [0.01, 0.05, 0.20],
    },
    {
        "id":         5,
        "name":       "Mariana Trench",
        "unlock_at":  22,
        "water_top":  [0.02, 0.05, 0.15],
        "water_deep": [0.005, 0.01, 0.05],
    },
]

LOCATIONS_BY_ID = {l["id"]: l for l in LOCATIONS}