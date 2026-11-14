from django.conf import settings
from django.db import transaction
from django.http import HttpResponseRedirect
from rest_framework import status
from rest_framework.exceptions import APIException
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from config import messages as msgs
from config.exceptions import NotFound

from .models import Payment
from .services import request_payment, verify_payment


class PaymentError(APIException):
    status_code = 502

    def __init__(self, persian: str, code: str = msgs.PAYMENT_FAILED):
        super().__init__({"detail": persian, "code": code})


class PayOrderView(APIView):
    """POST /api/orders/{id}/pay -> {payment_url, authority}."""

    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        try:
            order = request.user.orders.get(pk=pk)
        except Exception:
            raise NotFound()

        if order.payment_status != "unpaid":
            raise PaymentError(msgs.PERSIAN_ERRORS[msgs.PAYMENT_NOT_ALLOWED], msgs.PAYMENT_NOT_ALLOWED)
        if order.total is None or order.total <= 0:
            raise PaymentError(msgs.PERSIAN_ERRORS[msgs.PAYMENT_NOT_ALLOWED], msgs.PAYMENT_NOT_ALLOWED)

        shipping_method = request.data.get("shipping_method", "pickup")
        address = (request.data.get("address") or "").strip()
        if shipping_method == "delivery" and not address:
            return Response(
                {"detail": "برای ارسال، آدرس الزامی است.", "code": msgs.MISSING_FIELD},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if shipping_method not in ("pickup", "delivery"):
            shipping_method = "pickup"
        order.shipping_method = shipping_method
        order.address = address
        order.save(update_fields=["shipping_method", "address", "updated_at"])

        description = f"پرداخت سفارش شماره {order.id}"
        result = request_payment(order, description)

        payment = Payment.objects.create(
            order=order,
            authority=result.get("authority") or f"failed-{order.id}-{Payment.objects.count()}",
            amount_toman=order.total,
            amount_rial=order.total * 10,
            status="created",
            raw_response=result.get("raw") or {},
        )

        if not result["ok"]:
            payment.status = "failed"
            payment.raw_response = {"request": result.get("raw") or {}, "error": result.get("persian_error")}
            payment.save(update_fields=["status", "raw_response", "updated_at"])
            # Do not mark the order paid or failed permanently; user can retry.
            raise PaymentError(result["persian_error"])

        return Response({"payment_url": result["payment_url"], "authority": payment.authority})


def _result_redirect(order_id: int, ok: bool) -> HttpResponseRedirect:
    query = "payment=success" if ok else "payment=failed"
    if order_id:
        query += f"&order={order_id}"
    frontend = settings.FRONTEND_URL.rstrip("/")
    return HttpResponseRedirect(f"{frontend}/payment/result?{query}")


class ZarinpalCallbackView(APIView):
    """GET /api/payments/zarinpal/callback?Authority=...&Status=..."""

    permission_classes = [AllowAny]

    def get(self, request):
        authority = request.query_params.get("Authority") or ""
        gateway_status = request.query_params.get("Status") or ""

        payment = Payment.objects.filter(authority=authority).select_related("order").first()
        if not payment:
            return _result_redirect(0, ok=False)
        order = payment.order

        if gateway_status != "OK":
            if payment.status == "created":
                payment.status = "cancelled"
                payment.raw_response = {**(payment.raw_response or {}), "callback_status": gateway_status}
                payment.save(update_fields=["status", "raw_response", "updated_at"])
            return _result_redirect(order.id, ok=False)

        if payment.status == "paid":
            # Duplicate callback: idempotent success redirect, no second paid record.
            return _result_redirect(order.id, ok=True)

        result = verify_payment(payment, authority)
        payment.raw_response = {**(payment.raw_response or {}), "verify": result.get("raw") or {}}

        if result["ok"]:
            if result["already_paid"]:
                # Do not create a second paid record.
                if payment.status != "paid":
                    payment.ref_id = result["ref_id"] or payment.ref_id
                payment.save(update_fields=["ref_id", "raw_response", "updated_at"])
            else:
                payment.status = "paid"
                payment.ref_id = result["ref_id"] or ""
                payment.save(update_fields=["status", "ref_id", "raw_response", "updated_at"])

                with transaction.atomic():
                    locked_order = type(order).objects.select_for_update().get(pk=order.pk)
                    locked_order.payment_status = "paid"
                    if locked_order.status == "quoted":
                        locked_order.status = "confirmed"
                    locked_order.save(update_fields=["payment_status", "status", "updated_at"])
            return _result_redirect(order.id, ok=True)

        payment.status = "failed"
        payment.save(update_fields=["status", "raw_response", "updated_at"])
        return _result_redirect(order.id, ok=False)
