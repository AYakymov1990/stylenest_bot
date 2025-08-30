# app/scripts/reset_db.py
from __future__ import annotations
import argparse
import pathlib
import os
from sqlalchemy import text
from app.deps import SessionLocal
from app.config import settings
from app.models import User, Payment, Subscription, Base  # Base = declarative_base()

def _detect_sqlite_path() -> pathlib.Path | None:
    url = getattr(settings, "DATABASE_URL", "sqlite:///./stylenest.db")
    if url.startswith("sqlite"):
        # sqlite:///./stylenest.db  or sqlite:///stylenest.db
        raw = url.split("sqlite:///")[-1]
        return pathlib.Path(raw).resolve()
    return None

def soft_reset() -> None:
    """Чистим записи в таблицах, схема остаётся."""
    with SessionLocal() as db:
        # порядок важен, если есть FK
        db.query(Payment).delete()        # все платежи
        db.query(Subscription).delete()   # все подписки
        db.query(User).delete()           # все пользователи
        db.commit()
    print("✅ Soft reset: таблицы очищены.")

def hard_reset() -> None:
    """Удаляем файл SQLite и создаём схему заново."""
    db_path = _detect_sqlite_path()
    if db_path and db_path.exists():
        db_path.unlink()
        print(f"🗑️  Удалён файл БД: {db_path}")
    else:
        print("ℹ️  Файл БД не найден, создадим схему заново.")

    # пересоздаём схему
    with SessionLocal() as db:
        engine = db.get_bind()
        Base.metadata.create_all(bind=engine)
    print("✅ Hard reset: схема создана заново.")

def main():
    parser = argparse.ArgumentParser(description="Reset database")
    grp = parser.add_mutually_exclusive_group(required=True)
    grp.add_argument("--soft", action="store_true", help="Очистить таблицы (схему не трогать)")
    grp.add_argument("--hard", action="store_true", help="Удалить файл SQLite и пересоздать схему")
    args = parser.parse_args()

    if args.hard:
        hard_reset()
    else:
        soft_reset()

if __name__ == "__main__":
    main()
