import sys
import uuid
from datetime import datetime

sys.stdout.reconfigure(encoding='utf-8')

from database import get_engine, Base, User
from sqlalchemy.orm import sessionmaker

engine = get_engine()
Base.metadata.create_all(engine)
Session = sessionmaker(bind=engine)
db = Session()

existing = db.query(User).filter(User.username.in_(['ba_user', 'reviewer'])).all()
existing_names = [u.username for u in existing]

if 'ba_user' not in existing_names:
    db.add(User(id=str(uuid.uuid4()), username='ba_user', password='ba123',
                role='business_analyst', full_name='Alice (Business Analyst)',
                created_at=datetime.utcnow()))
if 'reviewer' not in existing_names:
    db.add(User(id=str(uuid.uuid4()), username='reviewer', password='rev123',
                role='reviewer', full_name='Bob (Reviewer)',
                created_at=datetime.utcnow()))

db.commit()

all_users = db.query(User).all()
for u in all_users:
    print(f"  {u.username} | {u.role} | {u.full_name}")

db.close()
print("Done.")
