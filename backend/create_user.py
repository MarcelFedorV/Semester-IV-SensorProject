import bcrypt
from database import SessionLocal, engine, Base
from models import User

Base.metadata.create_all(bind=engine)

def create_user(username: str, password: str, lang: str = "en"):
    db = SessionLocal()
    if db.query(User).filter(User.username == username).first():
        print(f"User '{username}' already exists.")
        db.close()
        return
    hashed = bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt())
    user = User(username=username, password=hashed.decode("utf-8"), role="user")
    db.add(user)
    db.commit()
    print(f"User '{username}' created successfully with role: user")
    db.close()

if __name__ == "__main__":
    create_user("john", "securepassword123")
    create_user("jan", "jan123")
    create_user("admin", "admin123")