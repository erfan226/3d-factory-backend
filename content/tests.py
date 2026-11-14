import io

from django.core.files.base import ContentFile
from django.test import TestCase
from PIL import Image
from rest_framework.test import APIClient

from .models import BlogPost, ContactMessage, SiteSetting


def _jpeg(size=(80, 60), color=(200, 180, 160)):
    buffer = io.BytesIO()
    Image.new("RGB", size, color).save(buffer, format="JPEG")
    return buffer.getvalue()


class SiteSettingTests(TestCase):
    def test_singleton_load(self):
        first = SiteSetting.load()
        second = SiteSetting.load()
        self.assertEqual(first.pk, second.pk)
        self.assertEqual(SiteSetting.objects.count(), 1)

    def test_endpoint(self):
        SiteSetting.load()
        client = APIClient()
        response = client.get("/api/site-setting")
        self.assertEqual(response.status_code, 200)
        self.assertIn("site_name", response.data)
        self.assertIn("accent_color", response.data)


class BlogTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.published = BlogPost.objects.create(
            title="راهنمای چاپ",
            slug="print-guide",
            summary="خلاصه",
            body="متن کامل",
            is_published=True,
            published_at="2026-01-01T10:00:00Z",
        )
        self.draft = BlogPost.objects.create(title="پیش‌نویس", slug="draft-post", summary="s", body="b")

    def test_list_shows_published_only(self):
        response = self.client.get("/api/blog")
        self.assertEqual(response.status_code, 200)
        slugs = [item["slug"] for item in response.data["results"]]
        self.assertIn("print-guide", slugs)
        self.assertNotIn("draft-post", slugs)

    def test_detail_published(self):
        response = self.client.get("/api/blog/print-guide")
        self.assertEqual(response.status_code, 200)
        self.assertIn("body", response.data)

    def test_detail_draft_404(self):
        response = self.client.get("/api/blog/draft-post")
        self.assertEqual(response.status_code, 404)


class ContactTests(TestCase):
    def test_submit_message(self):
        client = APIClient()
        response = client.post(
            "/api/contact",
            {
                "name": "علی رضایی",
                "email": "ali@example.com",
                "phone": "09120000000",
                "subject": "سفارش CNC",
                "body": "سلام، یک قطعه آلومینیومی نیاز دارم.",
            },
        )
        self.assertEqual(response.status_code, 201)
        self.assertEqual(ContactMessage.objects.count(), 1)
        message = ContactMessage.objects.first()
        self.assertFalse(message.is_read)

    def test_submit_requires_fields(self):
        client = APIClient()
        response = client.post("/api/contact", {"name": "x"})
        self.assertEqual(response.status_code, 400)
