# app/scripts/nudge_sub_end.py
from __future__ import annotations
import argparse
from datetime import datetime, timedelta, timezone

from app.deps import SessionLocal
from app.models import Subscription, SubscriptionStatus

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--tg_id", type=int, required=True, help="Telegram user id")
    ap.add_argument("--mode", choices=["3d","1d","expired"], required=True)
    args = ap.parse_args()

    with SessionLocal() as db:
        sub = db.query(Subscription).filter(
            Subscription.tg_id == args.tg_id,
            Subscription.status == SubscriptionStatus.active
        ).order_by(Subscription.id.desc()).first()

        if not sub:
            print("No active subscription found")
            return

        now = datetime.now(timezone.utc)
        if args.mode == "3d":
            sub.ends_at = now + timedelta(days=2, hours=12)  # в окно (2d,3d]
            sub.last_notified_3d = None
        elif args.mode == "1d":
            sub.ends_at = now + timedelta(hours=12)          # в окно (0,1d]
            sub.last_notified_1d = None
        else:
            sub.ends_at = now - timedelta(minutes=5)         # уже истекла
            sub.reminded_expired_at = None

        db.add(sub)
        db.commit()
        print("Updated ends_at:", sub.ends_at)

if __name__ == "__main__":
    main()
