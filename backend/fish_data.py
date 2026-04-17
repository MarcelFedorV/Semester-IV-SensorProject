

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
    },
    {
        "id": 2,
        "name": "Herring",
        "rarity": "Common",
        "depth": "surface",
        "fact": "Travels in massive schools of thousands.",
        "color": "#89CFF0",
        "sprite": "Herring.png",
    },
    {
        "id": 3,
        "name": "Perch",
        "rarity": "Common",
        "depth": "mid",
        "fact": "Recognizable by its striped pattern.",
        "color": "#F4A460",
        "sprite": "codfish.png",
    },
    {
        "id": 4,
        "name": "Carp",
        "rarity": "Common",
        "depth": "mid",
        "fact": "Can live for over 20 years.",
        "color": "#DAA520",
        "sprite": "codfish.png",
    },

    #  Uncommon 
    {
        "id": 5,
        "name": "Salmon",
        "rarity": "Uncommon",
        "depth": "mid",
        "fact": "Swims upstream to spawn where it was born.",
        "color": "#FA8072",
        "sprite": "dragonfish.png",
    },
    {
        "id": 6,
        "name": "Pike",
        "rarity": "Uncommon",
        "depth": "mid",
        "fact": "An aggressive predator with razor sharp teeth.",
        "color": "#6B8E23",
        "sprite": "dragonfish.png",
    },
    {
        "id": 7,
        "name": "Catfish",
        "rarity": "Uncommon",
        "depth": "deep",
        "fact": "Uses its whisker-like barbels to find food.",
        "color": "#808080",
        "sprite": "dragonfish.png",
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
    },
    {
        "id": 9,
        "name": "Oarfish",
        "rarity": "Rare",
        "depth": "deep",
        "fact": "The world's longest bony fish, up to 11 meters.",
        "color": "#C0C0C0",
        "sprite": "dragonfish.png",
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
    },
    {
        "id": 11,
        "name": "Golden Koi",
        "rarity": "Legendary",
        "depth": "deep",
        "fact": "Said to bring good luck to whoever catches one.",
        "color": "#FFD700",
        "sprite": "dragonfish.png",
    },
    {
        "id": 12,
        "name": "Alami Fish",
        "rarity": "Common",
        "depth": "surface",
        "fact": "This game is bad, why is it bad?.",
        "color": "#7BC67E",
        "sprite": "AlamiFish.png",
    },
]

# Quick lookup by id
FISH_BY_ID = {f["id"]: f for f in FISH}

# Grouped by rarity
FISH_BY_RARITY = {
    "Common":    [f for f in FISH if f["rarity"] == "Common"],
    "Uncommon":  [f for f in FISH if f["rarity"] == "Uncommon"],
    "Rare":      [f for f in FISH if f["rarity"] == "Rare"],
    "Legendary": [f for f in FISH if f["rarity"] == "Legendary"],
}