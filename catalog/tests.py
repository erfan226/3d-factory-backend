import io
from unittest.mock import patch

from django.core.files.base import ContentFile
from django.test import TestCase, override_settings
from PIL import Image
from rest_framework.test import APIClient

from accounts.models import User
from .models import (
    Category,
    CollectionItem,
    Comment,
    Like,
    Make,
    Material,
    Process,
    Product,
    ShowcaseFile,
    ShowcaseImage,
    ShowcaseItem,
    UserCollection,
)


def _image_file(name="photo.jpg", size=(80, 60)):
    buffer = io.BytesIO()
    Image.new("RGB", size, (180, 160, 140)).save(buffer, format="JPEG")
    return ContentFile(buffer.getvalue(), name=name)


class ShowcaseTestBase(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.process = Process.objects.create(name="FDM", slug="fdm", quote_type="estimate")
        cls.material = Material.objects.create(name="PLA", slug="pla", process=cls.process, colors=["white"])
        cls.category = Category.objects.create(name="Household", slug="household")

    def _make_item(self, slug="item-1", title="قطعه چاپی", allow_download=True, with_files=True, active=True):
        item = ShowcaseItem.objects.create(
            title=title,
            slug=slug,
            summary="خلاصه نمونه‌کار",
            description="توضیحات کامل با تنظیمات چاپ: لایه ۰.۲، Infill ۲۰٪، Support بله",
            category=self.category,
            process=self.process,
            material=self.material,
            allow_download=allow_download,
            is_active=active,
        )
        if with_files:
            ShowcaseImage.objects.create(item=item, image=_image_file(f"{slug}.jpg"), sort_order=0)
            ShowcaseFile.objects.create(
                item=item,
                file=ContentFile(b"solid x\nendsolid x\n", name=f"{slug}.stl"),
                original_name=f"{slug}.stl",
                file_type="stl",
                size_bytes=18,
            )
        return item

    def _user(self, email="user1@example.com"):
        return User.objects.create_user(email=email, password="StrongPass123", first_name="کاربر", last_name="یک")


class ShowcaseListTests(ShowcaseTestBase):
    def test_list_pagination_12(self):
        client = APIClient()
        for i in range(14):
            self._make_item(slug=f"item-{i}", title=f"مدل {i}")
        response = client.get("/api/showcase")
        self.assertEqual(response.status_code, 200)
        self.assertLessEqual(len(response.data["results"]), 12)
        first = response.data["results"][0]
        for field in ("likes_count", "makes_count", "comments_count", "downloads_count"):
            self.assertIn(field, first)

    def test_search_q(self):
        client = APIClient()
        self._make_item(slug="vase", title="گلدان سرامیکی")
        self._make_item(slug="clip", title="نگهدارنده کابل")
        response = client.get("/api/showcase?q=گلدان")
        self.assertEqual(len(response.data["results"]), 1)
        self.assertEqual(response.data["results"][0]["slug"], "vase")

    def test_filters_and_sort(self):
        client = APIClient()
        user = self._user()
        item_a = self._make_item(slug="a", title="A")
        item_b = self._make_item(slug="b", title="B")
        Like.objects.create(user=user, item=item_b)
        response = client.get("/api/showcase?sort=popular&category=household")
        self.assertEqual(response.data["results"][0]["slug"], "b")
        response = client.get("/api/showcase?process=fdm")
        self.assertEqual(response.data["count"], 2)

    def test_counts_annotation(self):
        client = APIClient()
        user = self._user()
        item = self._make_item()
        Like.objects.create(user=user, item=item)
        Comment.objects.create(user=user, item=item, body="عالی بود")
        Make.objects.create(user=user, item=item, photo=_image_file("make.jpg"), note="چاپ کردم")
        response = client.get("/api/showcase")
        row = response.data["results"][0]
        self.assertEqual(row["likes_count"], 1)
        self.assertEqual(row["comments_count"], 1)
        self.assertEqual(row["makes_count"], 1)


class ShowcaseDetailTests(ShowcaseTestBase):
    def test_detail_payload(self):
        client = APIClient()
        parent = self._make_item(slug="parent", title="اصلی")
        child = self._make_item(slug="child", title="بازطراحی")
        child.remixed_from = parent
        child.save()
        response = client.get("/api/showcase/parent")
        self.assertEqual(response.status_code, 200)
        self.assertIn("files", response.data)
        self.assertIn("images", response.data)
        self.assertIn("license", response.data)
        self.assertEqual(len(response.data["remixes"]), 1)
        self.assertIn("related_items", response.data)


class ShowcaseSocialTests(ShowcaseTestBase):
    def setUp(self):
        self.client = APIClient()
        self.user = self._user()
        self.item = self._make_item(slug="social", title="اجتماعی")

    def _auth(self):
        response = self.client.post(
            "/api/auth/login", {"email": self.user.email, "password": "StrongPass123"}
        )
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {response.data['access']}")

    def test_like_toggle(self):
        self._auth()
        response = self.client.post("/api/showcase/social/like")
        self.assertEqual(response.data["liked"], True)
        self.assertEqual(response.data["likes_count"], 1)
        response = self.client.post("/api/showcase/social/like")
        self.assertEqual(response.data["liked"], False)
        self.assertEqual(response.data["likes_count"], 0)
        self.assertEqual(Like.objects.count(), 0)

    def test_like_one_per_user(self):
        self._auth()
        self.client.post("/api/showcase/social/like")
        self.client.post("/api/showcase/social/like")
        self.assertEqual(Like.objects.count(), 0)

    def test_like_requires_auth(self):
        response = self.client.post("/api/showcase/social/like")
        self.assertEqual(response.status_code, 401)

    def test_save_to_named_collection_creates_it(self):
        self._auth()
        response = self.client.post(
            "/api/showcase/social/save", {"collection_name": "علاقه‌مندی‌ها"}, format="json"
        )
        self.assertEqual(response.status_code, 201)
        collection = UserCollection.objects.get(user=self.user, name="علاقه‌مندی‌ها")
        self.assertEqual(CollectionItem.objects.filter(collection=collection, item=self.item).count(), 1)

    def test_save_to_existing_collection(self):
        self._auth()
        collection = UserCollection.objects.create(user=self.user, name="لیست من")
        response = self.client.post(
            "/api/showcase/social/save", {"collection_id": collection.id}, format="json"
        )
        self.assertEqual(response.status_code, 201)
        self.assertEqual(CollectionItem.objects.count(), 1)

    def test_collections_list(self):
        self._auth()
        UserCollection.objects.create(user=self.user, name="لیست من")
        response = self.client.get("/api/collections")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data[0]["name"], "لیست من")

    def test_comment_create_and_list(self):
        self._auth()
        response = self.client.post(
            "/api/showcase/social/comments", {"body": "کیفیت چاپ عالی بود"}, format="json"
        )
        self.assertEqual(response.status_code, 201)
        response = self.client.get("/api/showcase/social/comments")
        self.assertEqual(response.data["results"][0]["body"], "کیفیت چاپ عالی بود")

    def test_make_create(self):
        self._auth()
        response = self.client.post(
            "/api/showcase/social/makes",
            {"photo": _image_file("make.jpg"), "note": "چاپ شد", "print_settings": "لایه ۰.۲"},
            format="multipart",
        )
        self.assertEqual(response.status_code, 201)
        response = self.client.get("/api/showcase/social/makes")
        self.assertEqual(len(response.data["results"]), 1)


class ShowcaseDownloadTests(ShowcaseTestBase):
    def setUp(self):
        self.client = APIClient()
        self.staff = User.objects.create_user(
            email="staff@example.com", password="StrongPass123", is_staff=True
        )

    def test_download_single_file_allowed_public(self):
        item = self._make_item(slug="dl-ok", allow_download=True)
        file_id = item.files.first().id
        response = self.client.get(f"/api/showcase/dl-ok/download?file_id={file_id}")
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"solid", b"".join(response.streaming_content))

    def test_download_zip_all(self):
        self._make_item(slug="dl-ok", allow_download=True)
        response = self.client.get("/api/showcase/dl-ok/download")
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"PK", b"".join(response.streaming_content))

    def test_download_blocked_when_not_allowed(self):
        self._make_item(slug="dl-no", allow_download=False)
        response = self.client.get("/api/showcase/dl-no/download")
        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.data["code"], "download_not_allowed")

    def test_staff_can_download_blocked_item(self):
        self._make_item(slug="dl-no", allow_download=False)
        self.client.force_authenticate(self.staff)
        response = self.client.get("/api/showcase/dl-no/download")
        self.assertEqual(response.status_code, 200)

    def test_zip_download_all(self):
        item = self._make_item(slug="zip")
        ShowcaseFile.objects.create(
            item=item,
            file=ContentFile(b"solid y\nendsolid y\n", name="second.stl"),
            original_name="second.stl",
            file_type="stl",
            size_bytes=18,
        )
        response = self.client.get("/api/showcase/zip/download")
        self.assertEqual(response.status_code, 200)
        self.assertIn("attachment", response.headers.get("Content-Disposition", ""))

    def test_download_increments_counter(self):
        self._make_item(slug="count")
        self.client.get("/api/showcase/count/download")
        self.client.get("/api/showcase/count/download")
        response = self.client.get("/api/showcase/count")
        self.assertEqual(response.data["downloads_count"], 2)


class ProductTests(ShowcaseTestBase):
    def setUp(self):
        self.client = APIClient()
        self.showcase = self._make_item(slug="linked")
        self.product = Product.objects.create(
            title="چاپ FDM سفارشی",
            slug="fdm-custom",
            description="توضیحات",
            showcase_item=self.showcase,
            process=self.process,
            material=self.material,
            price_from=250000,
            lead_time_days=3,
        )

    def test_list_price_from(self):
        response = self.client.get("/api/products")
        self.assertEqual(response.status_code, 200)
        row = response.data["results"][0]
        self.assertEqual(row["price_from"], 250000)
        self.assertEqual(row["lead_time_days"], 3)

    def test_detail_includes_showcase_link(self):
        response = self.client.get("/api/products/fdm-custom")
        self.assertEqual(response.data["showcase_item"]["slug"], "linked")


class CatalogBasicsTests(ShowcaseTestBase):
    def test_processes_endpoint(self):
        client = APIClient()
        response = client.get("/api/catalog/processes")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data[0]["slug"], "fdm")

    def test_materials_by_process(self):
        client = APIClient()
        response = client.get("/api/catalog/materials?process=fdm")
        self.assertEqual([m["slug"] for m in response.data], ["pla"])
