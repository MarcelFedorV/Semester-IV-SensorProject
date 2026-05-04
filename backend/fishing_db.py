# fishing_db.py
from sqlalchemy.orm import Session
from fishing_models import FishCatch, FishCollection, Achievement
from fish_data import FISH, MYSTERY_FISH_BY_LOCATION
from datetime import datetime

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

def save_achievement(db: Session, user_id: int, achievement_id: str) -> bool:
    """Save achievement, return True if it's new."""
    existing = db.query(Achievement).filter(
        Achievement.user_id == user_id,
        Achievement.achievement_id == achievement_id
    ).first()
    if existing:
        return False
    db.add(Achievement(
        user_id=user_id,
        achievement_id=achievement_id,
        unlocked_at=datetime.utcnow()
    ))
    db.commit()
    return True

def get_achievements(db: Session, user_id: int) -> list:
    rows = db.query(Achievement.achievement_id).filter(
        Achievement.user_id == user_id
    ).all()
    return [row[0] for row in rows]