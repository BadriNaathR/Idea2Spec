import sys
sys.stdout.reconfigure(encoding='utf-8')

from database import get_engine, User
from sqlalchemy.orm import sessionmaker

engine = get_engine()
Session = sessionmaker(bind=engine)
db = Session()

ba = db.query(User).filter(User.username == 'ba_user').first()
rev = db.query(User).filter(User.username == 'reviewer').first()

if ba:
    ba.full_name = 'Rama (Business Analyst)'
if rev:
    rev.full_name = 'Badri (Reviewer)'

db.commit()

for u in db.query(User).all():
    print(f"  {u.username} | {u.role} | {u.full_name}")

db.close()
