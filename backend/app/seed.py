from app.db import SessionLocal
from app.services.seed import seed_if_empty


def main() -> None:
    db = SessionLocal()
    try:
        seed_if_empty(db)
        db.commit()
        print("Seed complete. Demo accounts: demo_boss01 / demo_boss02")
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    main()
