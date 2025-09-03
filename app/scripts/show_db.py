# app/scripts/show_db.py
from __future__ import annotations

import argparse
from datetime import datetime, timezone, timedelta
from zoneinfo import ZoneInfo

from app.deps import SessionLocal
from app.models import User, Payment, Subscription, PaymentStatus, SubscriptionStatus

try:
    from rich.console import Console
    from rich.table import Table
    from rich.text import Text
    HAVE_RICH = True
except Exception:
    HAVE_RICH = False


def _to_aware_utc(dt: datetime | None) -> datetime | None:
    if dt is None:
        return None
    return dt if dt.tzinfo is not None else dt.replace(tzinfo=timezone.utc)

def _fmt_dt(dt: datetime | None, tz: str) -> str:
    dt = _to_aware_utc(dt)
    if dt is None:
        return "—"
    try:
        return dt.astimezone(ZoneInfo(tz)).strftime("%Y-%m-%d %H:%M:%S")
    except Exception:
        return dt.strftime("%Y-%m-%d %H:%M:%S %Z")

def _human_left(ends_at: datetime, now_utc: datetime) -> str:
    ends_at = _to_aware_utc(ends_at) or now_utc
    now_utc = _to_aware_utc(now_utc) or datetime.now(timezone.utc)
    delta = ends_at - now_utc
    secs = int(delta.total_seconds())
    sign = "" if secs >= 0 else "-"
    secs = abs(secs)
    days, rem = divmod(secs, 86400)
    hours, rem = divmod(rem, 3600)
    minutes, _ = divmod(rem, 60)
    core = f"{days}d {hours}h" if days else (f"{hours}h {minutes}m" if hours else f"{minutes}m")
    return f"{sign}{core}"

def _color_status_pay(s: PaymentStatus) -> str:
    return {
        PaymentStatus.approved: "green",
        PaymentStatus.pending: "yellow3",
        PaymentStatus.declined: "red",
        PaymentStatus.expired: "red",
    }.get(s, "white")

def _color_status_sub(s: SubscriptionStatus) -> str:
    return {
        SubscriptionStatus.active: "green",
        SubscriptionStatus.expired: "red",
        SubscriptionStatus.cancelled: "red",
    }.get(s, "white")


def show_users(console: Console | None, tz: str, limit: int):
    with SessionLocal() as db:
        rows = db.query(User).order_by(User.id.desc()).limit(limit).all()
    if not HAVE_RICH:
        print(f"\n[users] count={len(rows)} (limit {limit})")
        for u in rows:
            print(f"- id={u.id} tg_id={u.tg_id} username={u.username} created={_fmt_dt(u.created_at, tz)}")
        return
    table = Table(title=f"users (count={len(rows)}, limit={limit})")
    table.add_column("id", justify="right")
    table.add_column("tg_id", justify="right")
    table.add_column("username")
    table.add_column(f"created ({tz})")
    for u in rows:
        table.add_row(str(u.id), str(u.tg_id), str(u.username or "—"), _fmt_dt(u.created_at, tz))
    Console().print(table)

def show_payments(console: Console | None, tz: str, limit: int):
    with SessionLocal() as db:
        rows = db.query(Payment).order_by(Payment.id.desc()).limit(limit).all()
    if not HAVE_RICH:
        print(f"\n[payments] count={len(rows)} (limit {limit})")
        for p in rows:
            print(
                f"- id={p.id} tg_id={p.tg_id} tariff={p.tariff_code} "
                f"status={p.status} amount={p.amount}{p.currency} "
                f"created={_fmt_dt(p.created_at, tz)} approved={_fmt_dt(p.approved_at, tz)} "
                f"order_ref={p.order_reference}"
            )
        return
    table = Table(title=f"payments (count={len(rows)}, limit={limit})")
    table.add_column("id", justify="right")
    table.add_column("tg_id", justify="right")
    table.add_column("tariff")
    table.add_column("amount")
    table.add_column("status")
    table.add_column(f"created ({tz})")
    table.add_column(f"approved ({tz})")
    table.add_column("order_ref")
    for p in rows:
        status_text = Text(p.status.value, style=_color_status_pay(p.status))
        table.add_row(
            str(p.id), str(p.tg_id), p.tariff_code, f"{p.amount} {p.currency}",
            status_text, _fmt_dt(p.created_at, tz), _fmt_dt(p.approved_at, tz), p.order_reference
        )
    Console().print(table)

def show_subs(console: Console | None, tz: str, limit: int):
    now_utc = datetime.now(timezone.utc)
    with SessionLocal() as db:
        rows = db.query(Subscription).order_by(Subscription.id.desc()).limit(limit).all()
    if not HAVE_RICH:
        print(f"\n[subscriptions] count={len(rows)} (limit {limit})")
        for s in rows:
            left = _human_left(s.ends_at, now_utc)
            print(
                f"- id={s.id} tg_id={s.tg_id} tariff={s.tariff_code} status={s.status} "
                f"starts={_fmt_dt(s.starts_at, tz)} ends={_fmt_dt(s.ends_at, tz)} left={left} "
                f"rem3d={_fmt_dt(getattr(s,'reminded_3d_at', None), tz)} "
                f"rem1d={_fmt_dt(getattr(s,'reminded_1d_at', None), tz)} "
                f"remExp={_fmt_dt(getattr(s,'reminded_expired_at', None), tz)} "
                f"invite={'yes' if s.invite_link else '—'}"
            )
        return
    table = Table(title=f"subscriptions (count={len(rows)}, limit={limit})")
    table.add_column("id", justify="right")
    table.add_column("tg_id", justify="right")
    table.add_column("tariff")
    table.add_column("status")
    table.add_column(f"starts ({tz})")
    table.add_column(f"ends ({tz})")
    table.add_column("left")
    table.add_column("rem 3d")
    table.add_column("rem 1d")
    table.add_column("rem exp")
    table.add_column("invite")
    for s in rows:
        status_text = Text(s.status.value, style=_color_status_sub(s.status))
        table.add_row(
            str(s.id),
            str(s.tg_id),
            s.tariff_code,
            status_text,
            _fmt_dt(s.starts_at, tz),
            _fmt_dt(s.ends_at, tz),
            _human_left(s.ends_at, now_utc),
            _fmt_dt(getattr(s, "reminded_3d_at", None), tz),
            _fmt_dt(getattr(s, "reminded_1d_at", None), tz),
            _fmt_dt(getattr(s, "reminded_expired_at", None), tz),
            "yes" if s.invite_link else "—",
        )
    Console().print(table)

def main():
    ap = argparse.ArgumentParser(description="Pretty DB view")
    ap.add_argument("--limit", type=int, default=20)
    ap.add_argument("--tz", type=str, default="Europe/Warsaw")
    ap.add_argument("--only", choices=["all", "users", "payments", "subs"], default="all")
    args = ap.parse_args()

    console = Console() if HAVE_RICH else None
    if args.only in ("all", "users"):
        show_users(console, args.tz, args.limit)
    if args.only in ("all", "payments"):
        show_payments(console, args.tz, args.limit)
    if args.only in ("all", "subs"):
        show_subs(console, args.tz, args.limit)

if __name__ == "__main__":
    main()