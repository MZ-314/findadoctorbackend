"""
Run once to create initial company admin accounts.
Usage: python -m app.seed_admins
"""

from app.db import SessionLocal
from app import models
from passlib.context import CryptContext

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

ADMINS = [
    {
        "name":     "Staff Hyderabad",
        "email":    "staff.hyd@docfolio.com",
        "password": "StaffHyd@2026",
        "city":     "Hyderabad",
    },
    {
        "name":     "Staff Pune",
        "email":    "staff.pune@docfolio.com",
        "password": "StaffPun@2026",
        "city":     "Pune",
    },
    {
        "name":     "Staff Guwahati",
        "email":    "staff.ghy@docfolio.com",
        "password": "StaffGhy@2026",
        "city":     "Guwahati",
    },
]


def seed_admins():
    db = SessionLocal()
    try:
        for admin_data in ADMINS:
            existing = db.query(models.CompanyAdmin).filter(
                models.CompanyAdmin.email == admin_data["email"]
            ).first()
            if existing:
                print(f"Already exists: {admin_data['email']}")
                continue

            city = db.query(models.City).filter(
                models.City.name == admin_data["city"]
            ).first()
            if not city:
                print(f"City not found: {admin_data['city']}")
                continue

            admin = models.CompanyAdmin(
                name=admin_data["name"],
                email=admin_data["email"],
                password_hash=pwd_context.hash(admin_data["password"]),
                city_id=city.id,
                is_active=True
            )
            db.add(admin)
            print(f"Created: {admin_data['email']}")

        db.commit()
        print("\n✅ Company admins seeded!")
        print("\n── Staff credentials ─────────────────────────")
        for a in ADMINS:
            print(f"  {a['name']:<20} {a['email']}  /  {a['password']}")

    except Exception as e:
        db.rollback()
        print(f"❌ Failed: {e}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    seed_admins()