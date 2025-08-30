# app/payments/wayforpay.py
from __future__ import annotations

import time
import hashlib
import hmac
from typing import Tuple, Dict, Any, Iterable
from urllib.parse import urlparse

import httpx

from app.config import settings

__all__ = ["WayForPayClient", "build_signature"]


# -------- helpers --------

def build_signature(secret: str, fields: Iterable[str]) -> str:
    """
    Универсальный конструктор подписи WayForPay (HMAC-MD5).
    Поля должны быть в точном порядке согласно документации.
    """
    src = ";".join(map(str, fields))
    return hmac.new(secret.encode("utf-8"), src.encode("utf-8"), hashlib.md5).hexdigest()


def _hostname(domain_or_url: str) -> str:
    """
    Приводит merchantDomainName к хосту без схемы/слешей.
    """
    if not domain_or_url:
        return ""
    parsed = urlparse(domain_or_url)
    return parsed.netloc or domain_or_url.strip().replace("https://", "").replace("http://", "").strip("/")


# -------- client --------

class WayForPayClient:
    """
    Реальный клиент WayForPay для метода CREATE_INVOICE.

    Используем простую схему авторизации: `merchantAuthType = "SimpleSignature"`.
    Подпись: HMAC-MD5 от строки
        merchantAccount;
        merchantDomainName;
        orderReference;
        orderDate;
        amount;
        currency;
        productName[0];
        productCount[0];
        productPrice[0]
    """

    def __init__(self) -> None:
        self.api_url: str = getattr(settings, "WFP_API_URL", "https://api.wayforpay.com/api")
        self.merchant_account: str = settings.WFP_MERCHANT_ACCOUNT
        # нормализуем домен (должен быть без https://)
        self.merchant_domain: str = _hostname(settings.WFP_MERCHANT_DOMAIN)
        self.secret: str = settings.WFP_MERCHANT_SECRET
        self.currency: str = settings.WFP_CURRENCY

    # --- compose helpers ---

    def build_order_reference(self, tg_id: int, tariff_code: str) -> str:
        return f"tg{tg_id}_{int(time.time())}_{tariff_code}"

    def _signature_for_create_invoice(self, payload: Dict[str, Any]) -> str:
        fields = [
            payload["merchantAccount"],
            payload["merchantDomainName"],
            payload["orderReference"],
            payload["orderDate"],
            payload["amount"],
            payload["currency"],
            payload["productName"][0],
            payload["productCount"][0],
            payload["productPrice"][0],
        ]
        return build_signature(self.secret, fields)

    # --- public API ---

    async def create_invoice(self, *, tg_id: int, tariff_code: str, amount: int) -> Tuple[str, str, str]:
        """
        Создаёт счёт в WayForPay и возвращает:
            (order_reference, invoice_id, invoice_url)
        """
        order_reference = self.build_order_reference(tg_id, tariff_code)
        order_date = int(time.time())

        # форс-сумма для теста (если задана в .env), иначе боевое значение
        force_amount = int(getattr(settings, "WFP_FORCE_TEST_AMOUNT", 0) or 0)
        amount_to_pay = force_amount if force_amount > 0 else int(amount)

        payload: Dict[str, Any] = {
            "transactionType": "CREATE_INVOICE",
            "apiVersion": 1,                       # обязательный параметр
            "merchantAuthType": "SimpleSignature", # рекомендуемая авторизация
            "merchantAccount": self.merchant_account,
            "merchantDomainName": self.merchant_domain,
            "orderReference": order_reference,
            "orderDate": order_date,
            "amount": amount_to_pay,
            "currency": self.currency,
            "productName": [f"Subscription {tariff_code}"],
            "productCount": [1],
            "productPrice": [amount_to_pay],
            "language": "UA",
            "returnUrl": getattr(settings, "WFP_RETURN_URL", ""),
            "serviceUrl": settings.WFP_SERVICE_URL,  # серверный колбэк (должен быть HTTPS)
        }
        payload["merchantSignature"] = self._signature_for_create_invoice(payload)

        async with httpx.AsyncClient(timeout=20) as client:
            resp = await client.post(self.api_url, json=payload)
            # поднимаем сетевые/HTTP ошибки
            resp.raise_for_status()
            data: Dict[str, Any] = resp.json()

        # WayForPay при ошибке возвращает reasonCode/reason
        if "reasonCode" in data and data.get("invoiceUrl") is None and data.get("orderUrl") is None:
            raise RuntimeError(f"WayForPay createInvoice error: {data}")

        invoice_url: str = data.get("invoiceUrl") or data.get("orderUrl") or ""
        invoice_id: str = data.get("invoiceId") or order_reference

        if not invoice_url:
            # подстрахуемся на случай нестандартного ответа
            raise RuntimeError(f"WayForPay createInvoice: no invoice url in response: {data}")

        return order_reference, invoice_id, invoice_url

    # опционально: универсальная верификация подписи колбэка
    def verify_signature(self, data: Dict[str, Any], field_order: Iterable[str]) -> bool:
        """
        Проверяет подпись колбэка.
        Передай порядок полей согласно документации для конкретного типа колбэка
        (например, для TransactionStatus).
        Пример:
            fields = [
              data["merchantAccount"], data["orderReference"], data["amount"],
              data["currency"], data["authCode"], data["cardPan"],
              data["transactionStatus"], data["reasonCode"],
            ]
        """
        given = data.get("merchantSignature") or ""
        calc = build_signature(self.secret, [data[k] if isinstance(field_order, dict) else k for k in field_order])
        return given == calc
