"""ZarinPal payment gateway integration (v4 API).

All amounts cross the API boundary in Rial; the UI keeps Toman only.
Never log the merchant ID or any card data.
"""
import logging

import requests
from django.conf import settings

logger = logging.getLogger("payments")

REQUEST_PATH = "/pg/v4/payment/request.json"
VERIFY_PATH = "/pg/v4/payment/verify.json"
START_PAY_PATH = "/pg/StartPay/"


def _base_url() -> str:
    base = settings.ZARINPAL_BASE_URL.rstrip("/")
    return base or "https://payment.zarinpal.com"


def _merchant_id() -> str:
    return settings.ZARINPAL_MERCHANT_ID


def request_payment(order, description: str) -> dict:
    """Create a payment authority for the order.

    Returns {"ok": bool, "payment_url": str|None, "authority": str|None, "code": int|None,
             "persian_error": str|None, "raw": dict}.
    """
    # ZarinPal redirects the user's browser here; it must hit the Django
    # verification view, which then redirects to FRONTEND_URL/payment/result.
    callback_url = settings.ZARINPAL_CALLBACK_URL or f"{settings.FRONTEND_URL}/api/payments/zarinpal/callback"
    payload = {
        "merchant_id": _merchant_id(),
        "amount": order.total * 10,  # Toman -> Rial
        "callback_url": callback_url,
        "description": description,
        "metadata": {"order_id": order.id},
    }
    if order.user and order.user.email:
        payload["metadata"]["email"] = order.user.email

    url = f"{_base_url()}{REQUEST_PATH}"
    try:
        response = requests.post(url, json=payload, timeout=15)
        data = response.json().get("data") or {}
    except (requests.RequestException, ValueError) as exc:
        logger.warning("ZarinPal request failed for order %s: %s", order.id, exc)
        return {"ok": False, "payment_url": None, "authority": None, "code": None,
                "persian_error": "خطا در ارتباط با درگاه پرداخت.", "raw": {}}

    code = data.get("code")
    authority = data.get("authority")
    if code == 100 and authority:
        payment_url = f"{_base_url()}{START_PAY_PATH}{authority}"
        logger.info("ZarinPal payment created for order %s, authority=%s", order.id, authority)
        return {"ok": True, "payment_url": payment_url, "authority": authority,
                "code": code, "persian_error": None, "raw": data}

    logger.warning("ZarinPal request rejected for order %s, code=%s", order.id, code)
    return {"ok": False, "payment_url": None, "authority": None, "code": code,
            "persian_error": "ایجاد تراکنش پرداخت ناموفق بود.", "raw": data}


def verify_payment(payment, authority: str) -> dict:
    """Verify a callback authority against the stored amount (Rial, from DB).

    Returns {"ok": bool, "already_paid": bool, "ref_id": str|None, "code": int|None,
             "persian_error": str|None, "raw": dict}.
    """
    payload = {
        "merchant_id": _merchant_id(),
        "amount": payment.amount_rial,
        "authority": authority,
    }
    url = f"{_base_url()}{VERIFY_PATH}"
    try:
        response = requests.post(url, json=payload, timeout=15)
        data = response.json().get("data") or {}
    except (requests.RequestException, ValueError) as exc:
        logger.warning("ZarinPal verify failed for payment %s: %s", payment.id, exc)
        return {"ok": False, "already_paid": False, "ref_id": None, "code": None,
                "persian_error": "خطا در تایید پرداخت.", "raw": {}}

    code = data.get("code")
    ref_id = data.get("ref_id")
    if code == 100:
        logger.info("ZarinPal payment verified, authority=%s ref_id=%s", authority, ref_id)
        return {"ok": True, "already_paid": False, "ref_id": str(ref_id or ""), "code": code,
                "persian_error": None, "raw": data}
    if code == 101:
        logger.info("ZarinPal payment already verified, authority=%s", authority)
        return {"ok": True, "already_paid": True, "ref_id": str(ref_id or payment.ref_id or ""), "code": code,
                "persian_error": None, "raw": data}

    logger.warning("ZarinPal verify rejected, authority=%s code=%s", authority, code)
    return {"ok": False, "already_paid": False, "ref_id": None, "code": code,
            "persian_error": "تایید پرداخت ناموفق بود.", "raw": data}
