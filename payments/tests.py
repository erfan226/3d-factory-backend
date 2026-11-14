from datetime import date, timedelta
from unittest.mock import patch

from django.test import TestCase
from rest_framework.test import APIClient

from accounts.models import User
from catalog.models import Material, Process
from orders.models import CustomRequest, Order, Quote
from .models import Payment


class PaymentFlowTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.process = Process.objects.create(name="FDM", slug="fdm")
        cls.material = Material.objects.create(name="PLA", slug="pla", process=cls.process)

    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(email="buyer@example.com", password="StrongPass123")
        self.client.force_authenticate(self.user)
        custom_request = CustomRequest.objects.create(
            user=self.user, title="قطعه", process=self.process
        )
        quote = Quote.objects.create(
            custom_request=custom_request,
            price=500_000,
            lead_time_days=3,
            valid_until=date.today() + timedelta(days=7),
            status="accepted",
        )
        self.order = Order.objects.create(
            user=self.user, custom_request=custom_request, quote=quote, total=500_000, status="quoted"
        )

    def _pay(self):
        with patch(
            "payments.views.request_payment",
            return_value={
                "ok": True,
                "payment_url": "https://sandbox.zarinpal.com/pg/StartPay/AUTH1",
                "authority": "AUTH1",
                "code": 100,
                "persian_error": None,
                "raw": {"code": 100},
            },
        ):
            return self.client.post(f"/api/orders/{self.order.id}/pay", format="json")

    def test_pay_returns_payment_url(self):
        response = self._pay()
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(response.data["payment_url"], "https://sandbox.zarinpal.com/pg/StartPay/AUTH1")
        self.assertEqual(response.data["authority"], "AUTH1")
        payment = Payment.objects.get(authority="AUTH1")
        self.assertEqual(payment.amount_toman, 500_000)
        self.assertEqual(payment.amount_rial, 5_000_000)
        self.assertEqual(payment.status, "created")
        self.order.refresh_from_db()
        self.assertEqual(self.order.payment_status, "unpaid")

    def test_pay_requires_auth(self):
        self.client.force_authenticate(user=None)
        response = self.client.post(f"/api/orders/{self.order.id}/pay", format="json")
        self.assertEqual(response.status_code, 401)

    def test_pay_other_users_order_404(self):
        other = User.objects.create_user(email="other@example.com", password="StrongPass123")
        self.client.force_authenticate(other)
        response = self.client.post(f"/api/orders/{self.order.id}/pay", format="json")
        self.assertEqual(response.status_code, 404)

    def test_gateway_failure_marks_payment_failed_not_order(self):
        with patch(
            "payments.views.request_payment",
            return_value={"ok": False, "payment_url": None, "authority": None, "code": -9,
                          "persian_error": "ایجاد تراکنش پرداخت ناموفق بود.", "raw": {"code": -9}},
        ):
            response = self.client.post(f"/api/orders/{self.order.id}/pay", format="json")
        self.assertEqual(response.status_code, 502)
        self.assertEqual(response.data["code"], "payment_failed")
        self.assertEqual(Payment.objects.filter(status="failed").count(), 1)
        self.order.refresh_from_db()
        self.assertEqual(self.order.payment_status, "unpaid")

    def test_successful_callback_marks_order_paid_and_confirmed(self):
        self._pay()
        self.client.credentials()  # callback is public
        with patch(
            "payments.views.verify_payment",
            return_value={"ok": True, "already_paid": False, "ref_id": "REF9", "code": 100,
                          "persian_error": None, "raw": {"code": 100, "ref_id": "REF9"}},
        ):
            response = self.client.get("/api/payments/zarinpal/callback?Authority=AUTH1&Status=OK")
        self.assertEqual(response.status_code, 302)
        self.assertIn("payment=success", response.url)
        self.assertIn(f"order={self.order.id}", response.url)
        self.order.refresh_from_db()
        self.assertEqual(self.order.payment_status, "paid")
        self.assertEqual(self.order.status, "confirmed")
        payment = Payment.objects.get(authority="AUTH1")
        self.assertEqual(payment.status, "paid")
        self.assertEqual(payment.ref_id, "REF9")

    def test_duplicate_callback_is_idempotent(self):
        self._pay()
        self.client.credentials()
        verify = {"ok": True, "already_paid": False, "ref_id": "REF9", "code": 100,
                  "persian_error": None, "raw": {"code": 100}}
        with patch("payments.views.verify_payment", return_value=verify):
            self.client.get("/api/payments/zarinpal/callback?Authority=AUTH1&Status=OK")
        # Second callback with code 101 (already verified at the gateway)
        already = {"ok": True, "already_paid": True, "ref_id": "REF9", "code": 101,
                   "persian_error": None, "raw": {"code": 101}}
        with patch("payments.views.verify_payment", return_value=already):
            response = self.client.get("/api/payments/zarinpal/callback?Authority=AUTH1&Status=OK")
        self.assertEqual(response.status_code, 302)
        self.assertIn("payment=success", response.url)
        self.assertEqual(Payment.objects.count(), 1)
        self.order.refresh_from_db()
        self.assertEqual(self.order.payment_status, "paid")

    def test_callback_nok_marks_cancelled(self):
        self._pay()
        self.client.credentials()
        response = self.client.get("/api/payments/zarinpal/callback?Authority=AUTH1&Status=NOK")
        self.assertEqual(response.status_code, 302)
        self.assertIn("payment=failed", response.url)
        payment = Payment.objects.get(authority="AUTH1")
        self.assertEqual(payment.status, "cancelled")
        self.order.refresh_from_db()
        self.assertEqual(self.order.payment_status, "unpaid")

    def test_callback_unknown_authority_redirects_failure(self):
        response = self.client.get("/api/payments/zarinpal/callback?Authority=NOPE&Status=OK")
        self.assertEqual(response.status_code, 302)
        self.assertIn("payment=failed", response.url)

    def test_verify_failure_marks_payment_failed(self):
        self._pay()
        self.client.credentials()
        with patch(
            "payments.views.verify_payment",
            return_value={"ok": False, "already_paid": False, "ref_id": None, "code": -71,
                          "persian_error": "تایید پرداخت ناموفق بود.", "raw": {"code": -71}},
        ):
            response = self.client.get("/api/payments/zarinpal/callback?Authority=AUTH1&Status=OK")
        self.assertIn("payment=failed", response.url)
        payment = Payment.objects.get(authority="AUTH1")
        self.assertEqual(payment.status, "failed")
        self.order.refresh_from_db()
        self.assertEqual(self.order.payment_status, "unpaid")

    def test_delivery_requires_address(self):
        response = self.client.post(
            f"/api/orders/{self.order.id}/pay", {"shipping_method": "delivery"}, format="json"
        )
        self.assertEqual(response.status_code, 400)

    def test_already_paid_order_cannot_pay_again(self):
        self._pay()
        self.order.payment_status = "paid"
        self.order.save(update_fields=["payment_status"])
        response = self.client.post(f"/api/orders/{self.order.id}/pay", format="json")
        self.assertEqual(response.status_code, 502)
