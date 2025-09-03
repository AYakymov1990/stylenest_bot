# app/web/dashboard.py
from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Dict, Any

from flask import Flask, render_template, jsonify, request
from sqlalchemy import func, desc

from app.deps import SessionLocal
from app.models import User, Payment, Subscription, PaymentStatus, SubscriptionStatus

logger = logging.getLogger(__name__)

app = Flask(__name__, template_folder='templates')


def get_dashboard_stats() -> Dict[str, Any]:
    """Получает статистику для дашборда"""
    with SessionLocal() as db:
        # Общая статистика пользователей
        total_users = db.query(User).count()
        users_with_payments = db.query(User).join(
            Payment, User.tg_id == Payment.tg_id
        ).filter(
            Payment.status == PaymentStatus.approved
        ).distinct().count()
        users_without_payments = total_users - users_with_payments
        
        # Статистика платежей
        total_payments = db.query(Payment).count()
        approved_payments = db.query(Payment).filter(
            Payment.status == PaymentStatus.approved
        ).count()
        pending_payments = db.query(Payment).filter(
            Payment.status == PaymentStatus.pending
        ).count()
        
        # Статистика подписок
        total_subscriptions = db.query(Subscription).count()
        active_subscriptions = db.query(Subscription).filter(
            Subscription.status == SubscriptionStatus.active
        ).count()
        expired_subscriptions = db.query(Subscription).filter(
            Subscription.status == SubscriptionStatus.expired
        ).count()
        
        # Winback статистика
        users_winback_3d = db.query(User).filter(
            User.winback_3d_sent_at.isnot(None)
        ).count()
        users_winback_7d = db.query(User).filter(
            User.winback_7d_sent_at.isnot(None)
        ).count()
        users_winback_30d = db.query(User).filter(
            User.winback_30d_sent_at.isnot(None)
        ).count()
        
        # Доходы по тарифам
        revenue_by_tariff = db.query(
            Payment.tariff_code,
            func.sum(Payment.amount).label('total_amount'),
            func.count(Payment.id).label('count')
        ).filter(
            Payment.status == PaymentStatus.approved
        ).group_by(Payment.tariff_code).all()
        
        return {
            'users': {
                'total': total_users,
                'with_payments': users_with_payments,
                'without_payments': users_without_payments,
                'winback_3d': users_winback_3d,
                'winback_7d': users_winback_7d,
                'winback_30d': users_winback_30d,
            },
            'payments': {
                'total': total_payments,
                'approved': approved_payments,
                'pending': pending_payments,
                'revenue_by_tariff': [
                    {
                        'tariff': r.tariff_code,
                        'amount': r.total_amount,
                        'count': r.count
                    } for r in revenue_by_tariff
                ]
            },
            'subscriptions': {
                'total': total_subscriptions,
                'active': active_subscriptions,
                'expired': expired_subscriptions,
            }
        }


@app.route('/')
def dashboard():
    """Главная страница дашборда"""
    try:
        stats = get_dashboard_stats()
        return render_template('dashboard.html', stats=stats)
    except Exception as e:
        logger.error(f"Ошибка получения статистики: {e}")
        return f"Ошибка: {e}", 500


@app.route('/api/stats')
def api_stats():
    """API для получения статистики"""
    try:
        stats = get_dashboard_stats()
        return jsonify(stats)
    except Exception as e:
        logger.error(f"Ошибка API статистики: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/users')
def users_list():
    """Список пользователей"""
    try:
        with SessionLocal() as db:
            users = db.query(User).order_by(desc(User.created_at)).limit(100).all()
            return render_template('users.html', users=users)
    except Exception as e:
        logger.error(f"Ошибка получения пользователей: {e}")
        return f"Ошибка: {e}", 500


@app.route('/payments')
def payments_list():
    """Список платежей"""
    try:
        with SessionLocal() as db:
            payments = db.query(Payment).order_by(desc(Payment.created_at)).limit(100).all()
            return render_template('payments.html', payments=payments)
    except Exception as e:
        logger.error(f"Ошибка получения платежей: {e}")
        return f"Ошибка: {e}", 500


@app.route('/subscriptions')
def subscriptions_list():
    """Список подписок"""
    try:
        with SessionLocal() as db:
            subscriptions = db.query(Subscription).order_by(desc(Subscription.created_at)).limit(100).all()
            return render_template('subscriptions.html', subscriptions=subscriptions)
    except Exception as e:
        logger.error(f"Ошибка получения подписок: {e}")
        return f"Ошибка: {e}", 500


@app.route('/wfp/callback', methods=['POST'])
def wfp_callback():
    """Webhook для обработки платежей WayForPay"""
    try:
        # Получаем данные от WayForPay
        data = request.get_json() or request.form.to_dict()
        logger.info(f"[WFP] Получен webhook: {data}")
        
        # Здесь должна быть логика обработки платежа
        # Пока просто возвращаем OK
        return "OK", 200
        
    except Exception as e:
        logger.error(f"[WFP] Ошибка обработки webhook: {e}")
        return "ERROR", 400


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5001)
