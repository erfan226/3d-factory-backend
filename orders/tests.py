import io
from datetime import date, timedelta

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from rest_framework.test import APIClient

from accounts.models import User
from catalog.models import Material, Process
from content.models import SiteSetting
from .models import CustomRequest, Order, Quote


class OrdersTestBase(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.process = Process.objects.create(name="FDM", slug="fdm", quote_type="estimate")
        cls.material = Material.objects.create(name="PLA", slug="pla", process=cls.process)
        SiteSetting.load()

    def setUp(self):
        self.client = APIClient()

    def _register_and_auth(self, email="user@example.com"):
        self.client.post(
            "/api/auth/register",
            {"email": email, "password": "StrongPass123", "first_name": "علی", "last_name": "کریمی"},
        )
        response = self.client.post("/api/auth/login", {"email": email, "password": "StrongPass123"})
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {response.data['access']}")
        return User.objects.get(email=email)

    def _stl(self, name="part.stl"):
        return SimpleUploadedFile(name, b"solid cube\nendsolid cube\n", content_type="application/octet-stream")

    def _jpg(self, name="photo.jpg"):
        return SimpleUploadedFile(name, b"\xff\xd8\xff" + b"0" * 64, content_type="image/jpeg")

    def _payload(self, **overrides):
        data = {
            "title": "قطعه تستی",
            "process": "fdm",
            "material": "pla",
            "color": "white",
            "quantity": 2,
            "dimensions_text": "20x30x10 میلی‌متر",
            "intended_use": "پروتوتایپ",
            "notes": "در اسرع وقت",
        }
        data.update(overrides)
        return data


class CustomRequestTests(OrdersTestBase):
    def test_submit_with_stl(self):
        user = self._register_and_auth()
        response = self.client.post(
            "/api/custom-requests", {**self._payload(), "files": [self._stl()]}, format="multipart"
        )
        self.assertEqual(response.status_code, 201, response.data)
        self.assertEqual(response.data["status"], "received")
        custom_request = CustomRequest.objects.get(user=user)
        self.assertEqual(custom_request.files.count(), 1)
        self.assertEqual(custom_request.files.first().file_type, "stl")

    def test_submit_images_only_with_dimensions(self):
        self._register_and_auth()
        response = self.client.post(
            "/api/custom-requests",
            {**self._payload(), "files": [self._jpg(), self._jpg("photo2.jpg")]},
            format="multipart",
        )
        self.assertEqual(response.status_code, 201, response.data)

    def test_submit_images_only_without_dimensions_rejected(self):
        self._register_and_auth()
        payload = {**self._payload(dimensions_text=""), "files": [self._jpg()]}
        response = self.client.post("/api/custom-requests", payload, format="multipart")
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.data["code"], "validation_error")

    @override_settings(MAX_UPLOAD_SIZE_BYTES=64)
    def test_oversized_file_rejected(self):
        self._register_and_auth()
        big = SimpleUploadedFile("big.stl", b"x" * 100, content_type="application/octet-stream")
        response = self.client.post(
            "/api/custom-requests", {**self._payload(), "files": [big]}, format="multipart"
        )
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.data["code"], "file_too_large")
        self.assertIn("مگابایت", response.data["detail"])

    def test_invalid_file_type(self):
        self._register_and_auth()
        bad = SimpleUploadedFile("virus.exe", b"MZ" + b"0" * 32)
        response = self.client.post(
            "/api/custom-requests", {**self._payload(), "files": [bad]}, format="multipart"
        )
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.data["code"], "invalid_file_type")

    def test_max_five_files(self):
        self._register_and_auth()
        files = [SimpleUploadedFile(f"p{i}.stl", b"solid\nendsolid") for i in range(6)]
        response = self.client.post(
            "/api/custom-requests", {**self._payload(), "files": files}, format="multipart"
        )
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.data["code"], "too_many_files")

    def test_requires_auth(self):
        response = self.client.post("/api/custom-requests", self._payload(), format="multipart")
        self.assertEqual(response.status_code, 401)

    def test_list_own_only(self):
        self._register_and_auth("a@example.com")
        self.client.post(
            "/api/custom-requests", {**self._payload(), "files": [self._stl()]}, format="multipart"
        )
        self.client.credentials()
        self._register_and_auth("b@example.com")
        response = self.client.get("/api/custom-requests")
        self.assertEqual(response.data, [])

    def test_other_users_request_404(self):
        self._register_and_auth("a@example.com")
        self.client.post(
            "/api/custom-requests", {**self._payload(), "files": [self._stl()]}, format="multipart"
        )
        self.client.credentials()
        self._register_and_auth("b@example.com")
        other_id = CustomRequest.objects.first().id
        response = self.client.get(f"/api/custom-requests/{other_id}")
        self.assertEqual(response.status_code, 404)


class QuoteFlowTests(OrdersTestBase):
    def _make_request(self, email="user@example.com"):
        user = self._register_and_auth(email)
        self.client.post(
            "/api/custom-requests", {**self._payload(), "files": [self._stl()]}, format="multipart"
        )
        return user, CustomRequest.objects.get(user=user)

    def _quote(self, custom_request, valid_days=7, status="sent"):
        return Quote.objects.create(
            custom_request=custom_request,
            price=1_500_000,
            lead_time_days=5,
            message="پیشنهاد کارگاه",
            valid_until=date.today() + timedelta(days=valid_days),
            status=status,
        )

    def test_accept_creates_exactly_one_order(self):
        user, custom_request = self._make_request()
        quote = self._quote(custom_request)
        response = self.client.post(f"/api/custom-requests/{custom_request.id}/accept-quote")
        self.assertEqual(response.status_code, 200, response.data)
        self.assertIn("order_id", response.data)
        self.assertEqual(Order.objects.count(), 1)
        order = Order.objects.get(user=user)
        self.assertEqual(order.total, 1_500_000)
        self.assertEqual(order.quote, quote)
        self.assertEqual(order.status, "quoted")
        self.assertEqual(order.payment_status, "unpaid")
        quote.refresh_from_db()
        self.assertEqual(quote.status, "accepted")
        custom_request.refresh_from_db()
        self.assertEqual(custom_request.status, "quoted")

    def test_second_accept_returns_409(self):
        _, custom_request = self._make_request()
        self._quote(custom_request)
        self.client.post(f"/api/custom-requests/{custom_request.id}/accept-quote")
        response = self.client.post(f"/api/custom-requests/{custom_request.id}/accept-quote")
        self.assertEqual(response.status_code, 409)
        self.assertIn(response.data["code"], ("quote_already_used", "quote_not_sent"))
        self.assertEqual(Order.objects.count(), 1)

    def test_accept_expired_quote_409(self):
        _, custom_request = self._make_request()
        self._quote(custom_request, valid_days=-1)
        response = self.client.post(f"/api/custom-requests/{custom_request.id}/accept-quote")
        self.assertEqual(response.status_code, 409)
        self.assertEqual(response.data["code"], "quote_expired")
        self.assertEqual(Order.objects.count(), 0)

    def test_accept_draft_quote_409(self):
        _, custom_request = self._make_request()
        self._quote(custom_request, status="draft")
        response = self.client.post(f"/api/custom-requests/{custom_request.id}/accept-quote")
        self.assertEqual(response.status_code, 409)
        self.assertEqual(Order.objects.count(), 0)

    def test_reject_quote(self):
        _, custom_request = self._make_request()
        self._quote(custom_request)
        response = self.client.post(f"/api/custom-requests/{custom_request.id}/reject-quote")
        self.assertEqual(response.status_code, 200)
        quote = Quote.objects.first()
        self.assertEqual(quote.status, "rejected")

    def test_messages_endpoint(self):
        _, custom_request = self._make_request()
        response = self.client.post(
            f"/api/custom-requests/{custom_request.id}/messages",
            {"body": "سلام، وقتتون بخیر"},
            format="json",
        )
        self.assertEqual(response.status_code, 201)
        response = self.client.get(f"/api/custom-requests/{custom_request.id}")
        self.assertEqual(response.data["messages"][0]["body"], "سلام، وقتتون بخیر")

    def test_order_detail_own_only(self):
        _, custom_request = self._make_request()
        self._quote(custom_request)
        self.client.post(f"/api/custom-requests/{custom_request.id}/accept-quote")
        order_id = Order.objects.first().id
        self.client.credentials()
        self._register_and_auth("other@example.com")
        response = self.client.get(f"/api/orders/{order_id}")
        self.assertEqual(response.status_code, 404)


class OrderStatusProgressionTests(OrdersTestBase):
    def test_admin_action_moves_through_every_status(self):
        from django.contrib import admin as django_admin

        user = User.objects.create_user(email="u@example.com", password="StrongPass123")
        order = Order.objects.create(user=user, total=500_000, status="quoted")
        from orders.admin import OrderAdmin, STATUS_ORDER

        model_admin = OrderAdmin(Order, django_admin.site)
        queryset = Order.objects.filter(pk=order.pk)
        for _ in range(20):
            model_admin.advance_status(None, queryset)
            order.refresh_from_db()
            if order.status == "delivered":
                break
        self.assertEqual(order.status, "delivered")
