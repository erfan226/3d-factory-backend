from django.test import TestCase
from rest_framework.test import APIClient


class AuthFlowTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.register_payload = {
            "email": "customer@example.com",
            "password": "StrongPass123",
            "first_name": "Sara",
            "last_name": "Ahmadi",
        }

    def _register(self):
        return self.client.post("/api/auth/register", self.register_payload)

    def test_register_returns_tokens(self):
        response = self._register()
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data["email"], "customer@example.com")
        self.assertIn("access", response.data)
        self.assertIn("refresh", response.data)

    def test_register_duplicate_email_rejected(self):
        self._register()
        response = self._register()
        self.assertEqual(response.status_code, 400)

    def test_login_returns_tokens(self):
        self._register()
        response = self.client.post(
            "/api/auth/login", {"email": "customer@example.com", "password": "StrongPass123"}
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn("access", response.data)
        self.assertIn("refresh", response.data)

    def test_login_wrong_password(self):
        self._register()
        response = self.client.post(
            "/api/auth/login", {"email": "customer@example.com", "password": "wrong-password"}
        )
        self.assertEqual(response.status_code, 401)
        self.assertEqual(response.data.get("code"), "authentication_failed")

    def test_refresh_token(self):
        self._register()
        login = self.client.post(
            "/api/auth/login", {"email": "customer@example.com", "password": "StrongPass123"}
        )
        refresh = login.data["refresh"]
        response = self.client.post("/api/auth/refresh", {"refresh": refresh})
        self.assertEqual(response.status_code, 200)
        self.assertIn("access", response.data)

    def test_me_requires_auth(self):
        response = self.client.get("/api/auth/me")
        self.assertEqual(response.status_code, 401)

    def test_me_with_token(self):
        tokens = self._register().data
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {tokens['access']}")
        response = self.client.get("/api/auth/me")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["email"], "customer@example.com")
