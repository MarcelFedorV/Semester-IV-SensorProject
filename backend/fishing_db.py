# fishing_db.py
from sqlalchemy.orm import Session
from fishing_models import FishCatch, FishCollection, AchievementUnlock, PlayerStats
from fish_data import FISH, MYSTERY_FISH_BY_LOCATION
from datetime import datetime
from achievements import ACHIEVEMENTS_BY_ID, DISTANCE_ACHIEVEMENTS


def get_caught_ids(db: Session, user_id: int) -> set:
    rows = db.query(FishCollection.fish_id).filter(
        FishCollection.user_id == user_id
    ).all()
    return {row[0] for row in rows}

def save_catch(db: Session, user_id: int, fish_id: int, location_id: int, depth: float) -> bool:
    """Save catch, return True if it's a new fish."""
    # Add to catches log
    catch = FishCatch(
        user_id=user_id,
        fish_id=fish_id,
        location_id=location_id,
        depth=depth,
        caught_at=datetime.utcnow()
    )
    db.add(catch)

    # Add to collection if new
    existing = db.query(FishCollection).filter(
        FishCollection.user_id == user_id,
        FishCollection.fish_id == fish_id
    ).first()

    is_new = existing is None
    if is_new:
        collection_entry = FishCollection(
            user_id=user_id,
            fish_id=fish_id,
            first_caught_at=datetime.utcnow()
        )
        db.add(collection_entry)

    db.commit()
    return is_new

def get_collection(db: Session, user_id: int):
    """Returns all fish with caught status for this user."""
    caught = get_caught_ids(db, user_id)
    return [
        {**f, "caught": f["id"] in caught}
        for f in FISH
    ]

def check_location_complete(db: Session, user_id: int, location_id: int) -> bool:
    caught = get_caught_ids(db, user_id)
    location_fish_ids = {f["id"] for f in FISH if f["location_id"] == location_id}
    if not location_fish_ids:
        return False
    return location_fish_ids.issubset(caught)

def get_or_create_stats(db, user_id: int) -> PlayerStats:
    stats = db.query(PlayerStats).filter(PlayerStats.user_id == user_id).first()
    if not stats:
        stats = PlayerStats(user_id=user_id, total_distance_m=0.0, total_sessions=0)
        db.add(stats)
        db.commit()
    return stats

def add_distance(db, user_id: int, distance_m: float) -> list[str]:
    """Add distance and return list of newly unlocked achievement ids."""
    stats = get_or_create_stats(db, user_id)
    stats.total_distance_m += distance_m
    stats.updated_at = datetime.utcnow()
    db.commit()
    return check_distance_achievements(db, user_id, stats.total_distance_m)

def check_distance_achievements(db, user_id: int, total_m: float) -> list[str]:
    newly_unlocked = []
    for ach in DISTANCE_ACHIEVEMENTS:
        if total_m >= ach["threshold_m"]:
            if unlock_achievement(db, user_id, ach["id"]):
                newly_unlocked.append(ach["id"])
    return newly_unlocked

def unlock_achievement(db, user_id: int, achievement_id: str) -> bool:
    """Returns True if newly unlocked, False if already had it."""
    existing = db.query(AchievementUnlock).filter(
        AchievementUnlock.user_id == user_id,
        AchievementUnlock.achievement_id == achievement_id
    ).first()
    if existing:
        return False
    db.add(AchievementUnlock(
        user_id=user_id,
        achievement_id=achievement_id,
        unlocked_at=datetime.utcnow()
    ))
    db.commit()
    return True

def get_unlocked_achievements(db, user_id: int) -> list[str]:
    rows = db.query(AchievementUnlock.achievement_id).filter(
        AchievementUnlock.user_id == user_id
    ).all()
    return [r[0] for r in rows]

def get_stats(db, user_id: int) -> dict:
    stats = get_or_create_stats(db, user_id)
    return {
        "total_distance_m":  stats.total_distance_m,
        "total_distance_km": round(stats.total_distance_m / 1000, 2),
        "total_sessions":    stats.total_sessions,
    }

def check_fishing_achievements(db, user_id: int, fish: dict, caught_ids: set) -> list[str]:
    newly_unlocked = []

    def try_unlock(ach_id):
        if unlock_achievement(db, user_id, ach_id):
            newly_unlocked.append(ach_id)

    # First catch
    if len(caught_ids) == 1:
        try_unlock("first_catch")

    # Legendary catch
    if fish.get("rarity") == "Legendary":
        try_unlock("lucky_day")

    # Mystery/Location Legend
    if fish.get("rarity") == "Location Legend":
        try_unlock("mystery_first")

    # Collection milestones
    normal_fish = [f for f in FISH]
    if len(caught_ids) >= 10:
        try_unlock("collector_10")
    if len(caught_ids) >= 25:
        try_unlock("collector_25")
    if len(caught_ids) >= len(normal_fish):
        try_unlock("collector_all")

    # Location masters
    location_map = {1: "baltic_master", 2: "north_master", 3: "caribbean_master",
                    4: "pacific_master", 5: "trench_master"}
    for loc_id, ach_id in location_map.items():
        loc_fish_ids = {f["id"] for f in FISH if f["location_id"] == loc_id}
        if loc_fish_ids and loc_fish_ids.issubset(caught_ids):
            try_unlock(ach_id)

    return newly_unlocked