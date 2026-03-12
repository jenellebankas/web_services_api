# scripts/create_admin_key.py
"""
scripts/create_admin_key.py

Run once after deployment to seed the first API key in the production database.
The generated key is printed once — store it somewhere safe (e.g. a password manager).

Usage:
    python scripts/create_admin_key.py
"""
import os
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from datetime import datetime
from sqlalchemy.orm import Session
from app.database import SessionLocal, engine
from app.models import Base, APIKey

Base.metadata.create_all(bind=engine)

db: Session = SessionLocal()

existing = db.query(APIKey).filter_by(name="admin").first()
if existing:
    print(f"Admin key already exists (id={existing.id}). Aborting.")
    db.close()
    sys.exit(0)

key_value = APIKey.generate()
admin_key = APIKey(
    key=key_value,
    name="admin",
    is_active=True,
    created_at=datetime.utcnow(),
)
db.add(admin_key)
db.commit()
db.close()

print("=" * 60)
print("Admin API key created. Store this — it will not be shown again.")
print(f"  Key: {key_value}")
print("=" * 60)
print("Set this as the API_KEY environment variable in:")
print("  - Render (Environment tab)")
print("  - Streamlit Cloud (Secrets)")
