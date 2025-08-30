# app/scripts/show_db.py
from __future__ import annotations
import argparse
from datetime import datetime
from app.deps import SessionLocal
from app.models import User, Payment, Subscription

def _fmt_dt(v):
    if not v:
        return ""
    try:
        return v.astimezone().strftime("%Y-%m-%d %H:%M")
    except Exception:
        return str(v)

def show_summary(limit: int):
    with SessionLocal() as db:
        users = db.query(User).count()
        pays_all = db.query(Payment).count()
        pays_ok = db.query(Payment).filter(Payment.status == "approved").count()
        subs_all = db.query(Subscription).count()
        subs_active = db.query(Subscription).filter(Subscription.status == "active").count()

        print("===== SUMMARY =====")
        print(f"Users:          {users}")
        print(f"Payments:       {pays_all} (approved: {pays_ok})")
        print(f"Subscriptions:  {subs_all} (active: {subs_active})")
        print()

        print(f"===== LAST {limit} PAYMENTS =====")
        q = db.query(Payment).order_by(Payment.id.desc()).limit(limit).all()
        print(f"{'id':>4} {'tg_id':>12} {'tariff':>6} {'amt':>6} {'cur':>4} {'status':>9} {'paid_at':>17} {'order_ref':>22}")
        for p in q:
            print(f"{getattr(p,'id',''):>4} {p.tg_id:>12} {p.tariff_code:>6} "
                  f"{p.amount:>6} {p.currency:>4} {p.status:>9} "
                  f"{_fmt_dt(getattr(p,'paid_at',None)):>17} {p.order_reference:>22}")

        print()
        print(f"===== LAST {limit} SUBSCRIPTIONS =====")
        s = db.query(Subscription).order_by(Subscription.id.desc()).limit(limit).all()
        print(f"{'id':>4} {'tg_id':>12} {'tariff':>6} {'status':>9} {'starts_at':>17} {'ends_at':>17}")
        for sub in s:
            print(f"{getattr(sub,'id',''):>4} {sub.tg_id:>12} {sub.tariff_code:>6} "
                  f"{sub.status:>9} {_fmt_dt(sub.starts_at):>17} {_fmt_dt(sub.ends_at):>17}")

        print()
        print(f"===== LAST {limit} USERS =====")
        u = db.query(User).order_by(User.id.desc()).limit(limit).all()
        print(f"{'id':>4} {'tg_id':>12} {'username':>18} {'created_at':>17}")
        for x in u:
            print(f"{getattr(x,'id',''):>4} {x.tg_id:>12} {str(getattr(x,'username','')):>18} {_fmt_dt(getattr(x,'created_at',None)):>17}")

def main():
    parser = argparse.ArgumentParser(description="Show DB snapshot")
    parser.add_argument("--limit", type=int, default=20, help="Сколько записей выводить в разделах")
    args = parser.parse_args()
    show_summary(args.limit)

if __name__ == "__main__":
    main()
