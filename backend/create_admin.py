import bcrypt
from database import SessionLocal, engine, Base
from models import User

Base.metadata.create_all(bind=engine)

def create_admin(username: str, password: str):
    db = SessionLocal()
    if db.query(User).filter(User.username == username).first():
        print(f"User '{username}' already exists.")
        db.close()
        return
    hashed = bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt())
    user = User(username=username, password=hashed.decode("utf-8"), role="admin")
    db.add(user)
    db.commit()
    print(f"Admin user '{username}' created successfully with role: admin")
    db.close()

if __name__ == "__main__":
    create_admin("admin", "admin123")
