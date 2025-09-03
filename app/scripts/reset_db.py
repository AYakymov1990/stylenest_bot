# app/scripts/reset_db.py
from __future__ import annotations
import argparse
import os
import sys
from urllib.parse import urlparse
import subprocess

from app.config import settings

def _sqlite_path_from_url(db_url: str) -> str | None:
    # ожидаем что DATABASE_URL вида sqlite:///absolute/path.db или sqlite:///stylenest.db
    if not db_url.startswith("sqlite"):
        return None
    parsed = urlparse(db_url)
    # для sqlite:///... parsed.path уже абсолютный/относительный путь
    return parsed.path or None

def hard_reset(run_alembic: bool) -> None:
    db_url = settings.DATABASE_URL
    db_path = _sqlite_path_from_url(db_url)
    if not db_path:
        print(f"❌ Hard reset сейчас поддержан только для sqlite, у тебя: {db_url}")
        sys.exit(1)

    # удаляем файл БД и журналы
    for p in [db_path, db_path + "-shm", db_path + "-wal"]:
        try:
            if os.path.exists(p):
                os.remove(p)
                print(f"🗑️  Удалён: {p}")
        except Exception as e:
            print(f"⚠️  Не удалось удалить {p}: {e}")

    if run_alembic:
        # поднимаем схему ТОЛЬКО миграциями
        print("▶️  alembic upgrade head ...")
        subprocess.check_call(["alembic", "upgrade", "head"])

def main():
    ap = argparse.ArgumentParser(description="Reset local SQLite DB managed by Alembic")
    ap.add_argument("--hard", action="store_true", help="Delete SQLite file(s)")
    ap.add_argument("--upgrade", action="store_true", help="Run `alembic upgrade head` after reset")
    args = ap.parse_args()

    if args.hard:
        hard_reset(run_alembic=args.upgrade)
    else:
        print("Use --hard to delete the SQLite DB file. Example: python -m app.scripts.reset_db --hard --upgrade")

if __name__ == "__main__":
    main()
