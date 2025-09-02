"""subscription reminders flags

Revision ID: 304fcc839f4a
Revises: c23e0db13390
Create Date: 2025-09-02 00:00:00.000000
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "304fcc839f4a"
down_revision: Union[str, None] = "c23e0db13390"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _column_exists(table: str, column: str) -> bool:
    bind = op.get_bind()
    insp = sa.inspect(bind)
    names = [c["name"] for c in insp.get_columns(table)]
    return column in names


def _index_exists(table: str, index_name: str) -> bool:
    bind = op.get_bind()
    insp = sa.inspect(bind)
    try:
        names = [ix["name"] for ix in insp.get_indexes(table)]
        return index_name in names
    except Exception:
        return False


def upgrade() -> None:
    bind = op.get_bind()

    # На SQLite нельзя менять тип столбца напрямую — пропускаем.
    if bind.dialect.name != "sqlite":
        op.alter_column(
            "payments",
            "tariff_code",
            existing_type=sa.String(length=8),
            type_=sa.String(length=10),
            existing_nullable=False,
        )

    # Добавляем колонки только если их ещё нет.
    if not _column_exists("subscriptions", "last_notified_3d"):
        op.add_column(
            "subscriptions",
            sa.Column("last_notified_3d", sa.DateTime(timezone=True), nullable=True),
        )
    if not _column_exists("subscriptions", "last_notified_1d"):
        op.add_column(
            "subscriptions",
            sa.Column("last_notified_1d", sa.DateTime(timezone=True), nullable=True),
        )

    # Индекс по (tg_id, status), создаём если нет.
    if not _index_exists("subscriptions", "ix_subs_tg_id_status"):
        op.create_index(
            "ix_subs_tg_id_status", "subscriptions", ["tg_id", "status"], unique=False
        )


def downgrade() -> None:
    # Откаты идемпотентно
    if _index_exists("subscriptions", "ix_subs_tg_id_status"):
        op.drop_index("ix_subs_tg_id_status", table_name="subscriptions")

    if _column_exists("subscriptions", "last_notified_1d"):
        op.drop_column("subscriptions", "last_notified_1d")

    if _column_exists("subscriptions", "last_notified_3d"):
        op.drop_column("subscriptions", "last_notified_3d")

    bind = op.get_bind()
    if bind.dialect.name != "sqlite":
        op.alter_column(
            "payments",
            "tariff_code",
            existing_type=sa.String(length=10),
            type_=sa.String(length=8),
            existing_nullable=False,
        )
