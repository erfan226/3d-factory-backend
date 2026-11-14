import os
import tempfile
import zipfile

from django.contrib.admin.views.decorators import staff_member_required  # noqa: F401
from django.db.models import Count, Q
from django.http import FileResponse, HttpResponse
from rest_framework import status
from rest_framework.exceptions import APIException
from rest_framework.generics import ListAPIView, ListCreateAPIView, RetrieveAPIView
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from config import messages as msgs
from config.settings import MAX_ZIP_SIZE_BYTES

from .models import (
    Category,
    CollectionItem,
    DownloadLog,
    Like,
    Make,
    Material,
    Process,
    Product,
    ShowcaseFile,
    ShowcaseItem,
    UserCollection,
)
from .pagination import CommentPagination, DefaultPagination
from .serializers import (
    CategorySerializer,
    CollectionItemSerializer,
    CommentSerializer,
    MakeSerializer,
    MaterialSerializer,
    ProcessSerializer,
    ProductCardSerializer,
    ProductDetailSerializer,
    ShowcaseItemCardSerializer,
    ShowcaseItemDetailSerializer,
    UserCollectionSerializer,
)


class NotFoundException(APIException):
    status_code = 404

    def __init__(self):
        super().__init__({"detail": msgs.PERSIAN_ERRORS[msgs.NOT_FOUND], "code": msgs.NOT_FOUND})


class CatalogFilterMixin:
    @staticmethod
    def annotate_counts(queryset):
        return queryset.annotate(
            likes_count=Count("likes", distinct=True),
            downloads_count=Count("download_logs", distinct=True),
            makes_count=Count("makes", distinct=True),
            comments_count=Count("comments", filter=Q(comments__is_visible=True), distinct=True),
        )


class ProcessListView(ListAPIView):
    serializer_class = ProcessSerializer
    permission_classes = [AllowAny]
    pagination_class = None

    def get_queryset(self):
        qs = Process.objects.all()
        if self.request.query_params.get("is_active") == "true":
            qs = qs.filter(is_active=True)
        return qs


class MaterialListView(ListAPIView):
    serializer_class = MaterialSerializer
    permission_classes = [AllowAny]
    pagination_class = None

    def get_queryset(self):
        qs = Material.objects.select_related("process")
        process_slug = self.request.query_params.get("process")
        if process_slug:
            qs = qs.filter(process__slug=process_slug)
        return qs


class CategoryListView(ListAPIView):
    serializer_class = CategorySerializer
    permission_classes = [AllowAny]
    pagination_class = None
    queryset = Category.objects.all()


class ShowcaseListView(ListAPIView, CatalogFilterMixin):
    serializer_class = ShowcaseItemCardSerializer
    permission_classes = [AllowAny]
    pagination_class = DefaultPagination

    def get_queryset(self):
        qs = self.annotate_counts(
            ShowcaseItem.objects.filter(is_active=True).select_related("category", "process", "material")
        )
        params = self.request.query_params

        q = params.get("q", "").strip()
        if q:
            qs = qs.filter(
                Q(title__icontains=q)
                | Q(summary__icontains=q)
                | Q(description__icontains=q)
                | Q(tags__name__icontains=q)
            ).distinct()

        for param, lookup in (
            ("category", "category__slug"),
            ("tag", "tags__slug"),
            ("process", "process__slug"),
            ("material", "material__slug"),
        ):
            value = params.get(param)
            if value:
                qs = qs.filter(**{lookup: value})

        sort = params.get("sort", "newest")
        if sort == "popular":
            qs = qs.order_by("-likes_count", "-created_at")
        elif sort == "most_makes":
            qs = qs.order_by("-makes_count", "-created_at")
        else:
            qs = qs.order_by("-created_at")

        if params.get("featured") == "true":
            qs = qs.filter(is_featured=True)
        return qs


class ShowcaseDetailView(RetrieveAPIView, CatalogFilterMixin):
    serializer_class = ShowcaseItemDetailSerializer
    permission_classes = [AllowAny]
    lookup_field = "slug"

    def get_queryset(self):
        return self.annotate_counts(
            ShowcaseItem.objects.filter(is_active=True).select_related("category", "process", "material")
        ).prefetch_related("tags", "files", "images")

    def retrieve(self, request, *args, **kwargs):
        item = self.get_object()
        data = self.get_serializer(item).data
        related = self.annotate_counts(
            ShowcaseItem.objects.filter(is_active=True, category=item.category)
            .exclude(id=item.id)
            .select_related("category", "process", "material")
        )[:6]
        if not related:
            related = self.annotate_counts(
                ShowcaseItem.objects.filter(is_active=True)
                .exclude(id=item.id)
                .select_related("category", "process", "material")
            )[:6]
        data["related_items"] = ShowcaseItemCardSerializer(related, many=True).data
        data["liked_by_me"] = bool(
            request.user.is_authenticated and Like.objects.filter(user=request.user, item=item).exists()
        )
        data["saved_in_collections"] = list(
            UserCollection.objects.filter(
                user=request.user, items__item=item
            ).values_list("id", flat=True)
        ) if request.user.is_authenticated else []
        data["orderable"] = item.products.filter(is_active=True).exists()
        return Response(data)


class LikeToggleView(APIView, CatalogFilterMixin):
    permission_classes = [IsAuthenticated]

    def post(self, request, slug):
        item = ShowcaseItem.objects.filter(slug=slug, is_active=True).first()
        if not item:
            raise NotFoundException()
        like, created = Like.objects.get_or_create(user=request.user, item=item)
        if not created:
            like.delete()
        likes_count = Like.objects.filter(item=item).count()
        return Response({"liked": created, "likes_count": likes_count})


class SaveToCollectionView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, slug):
        item = ShowcaseItem.objects.filter(slug=slug, is_active=True).first()
        if not item:
            raise NotFoundException()
        collection_id = request.data.get("collection_id")
        collection_name = (request.data.get("collection_name") or "").strip()
        if collection_id:
            collection = UserCollection.objects.filter(user=request.user, id=collection_id).first()
            if not collection:
                raise NotFoundException()
        elif collection_name:
            collection, _ = UserCollection.objects.get_or_create(
                user=request.user,
                name=collection_name[:100],
                defaults={"description": ""},
            )
        else:
            return Response(
                {"detail": "شناسه یا نام مجموعه لازم است.", "code": msgs.MISSING_FIELD},
                status=status.HTTP_400_BAD_REQUEST,
            )
        _, created = CollectionItem.objects.get_or_create(collection=collection, item=item)
        return Response(
            {
                "collection": UserCollectionSerializer(collection).data,
                "created": created,
            },
            status=status.HTTP_201_CREATED,
        )


class CollectionListCreateView(ListCreateAPIView):
    serializer_class = UserCollectionSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = None

    def get_queryset(self):
        return UserCollection.objects.filter(user=self.request.user).annotate(item_count=Count("items", distinct=True))

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)


class CollectionDetailView(RetrieveAPIView):
    serializer_class = UserCollectionSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return UserCollection.objects.filter(user=self.request.user).annotate(item_count=Count("items", distinct=True))

    def retrieve(self, request, *args, **kwargs):
        collection = self.get_object()
        data = self.get_serializer(collection).data
        items = CollectionItem.objects.filter(collection=collection).select_related(
            "item__category", "item__process", "item__material"
        )
        data["items"] = CollectionItemSerializer(items, many=True).data
        return Response(data)


class CommentListCreateView(ListCreateAPIView):
    serializer_class = CommentSerializer
    pagination_class = CommentPagination

    def get_permissions(self):
        return [IsAuthenticated()] if self.request.method == "POST" else [AllowAny()]

    def get_item(self):
        item = ShowcaseItem.objects.filter(slug=self.kwargs["slug"], is_active=True).first()
        if not item:
            raise NotFoundException()
        return item

    def get_queryset(self):
        return self.get_item().comments.filter(is_visible=True).select_related("user")

    def perform_create(self, serializer):
        serializer.save(user=self.request.user, item=self.get_item())


class MakeListCreateView(ListCreateAPIView):
    serializer_class = MakeSerializer
    pagination_class = CommentPagination

    def get_permissions(self):
        return [IsAuthenticated()] if self.request.method == "POST" else [AllowAny()]

    def get_item(self):
        item = ShowcaseItem.objects.filter(slug=self.kwargs["slug"], is_active=True).first()
        if not item:
            raise NotFoundException()
        return item

    def get_queryset(self):
        return self.get_item().makes.select_related("user")

    def perform_create(self, serializer):
        serializer.save(user=self.request.user, item=self.get_item())


class DownloadNotAllowed(APIException):
    status_code = 403

    def __init__(self):
        super().__init__(
            {"detail": msgs.PERSIAN_ERRORS[msgs.DOWNLOAD_NOT_ALLOWED], "code": msgs.DOWNLOAD_NOT_ALLOWED}
        )


class ShowcaseDownloadView(APIView):
    """Serve a single file or a zip of all files; log every download."""

    permission_classes = [AllowAny]

    def get(self, request, slug):
        item = ShowcaseItem.objects.filter(slug=slug, is_active=True).first()
        if not item:
            raise NotFoundException()
        if not item.allow_download and not (request.user.is_authenticated and request.user.is_staff):
            raise DownloadNotAllowed()

        file_id = request.query_params.get("file_id")
        if file_id:
            showcase_file = item.files.filter(id=file_id).first()
            if not showcase_file:
                raise NotFoundException()
            DownloadLog.objects.create(
                user=request.user if request.user.is_authenticated else None,
                item=item,
                file=showcase_file,
            )
            response = FileResponse(showcase_file.file.open("rb"), as_attachment=True)
            response["Content-Disposition"] = f'attachment; filename="{os.path.basename(showcase_file.file.name)}"'
            return response

        # Zip all files, capped at MAX_ZIP_SIZE_BYTES of source content.
        files = list(item.files.all())
        if not files:
            raise NotFoundException()
        total_size = sum(f.size_bytes or 0 for f in files)
        if total_size > MAX_ZIP_SIZE_BYTES:
            return Response(
                {"detail": "حجم مجموع فایل‌ها برای دانلود یکجا بیش از حد مجاز است.", "code": msgs.FILE_TOO_LARGE},
                status=status.HTTP_400_BAD_REQUEST,
            )
        DownloadLog.objects.create(
            user=request.user if request.user.is_authenticated else None, item=item, is_zip=True
        )
        tmp = tempfile.NamedTemporaryFile(suffix=".zip", delete=False)
        with zipfile.ZipFile(tmp, "w", zipfile.ZIP_DEFLATED) as archive:
            for showcase_file in files:
                with showcase_file.file.open("rb") as source:
                    archive.writestr(showcase_file.original_name, source.read())
        tmp.close()
        response = FileResponse(open(tmp.name, "rb"), as_attachment=True)
        response["Content-Disposition"] = f'attachment; filename="{item.slug}.zip"'
        return response


class ProductListView(ListAPIView):
    serializer_class = ProductCardSerializer
    permission_classes = [AllowAny]
    pagination_class = DefaultPagination

    def get_queryset(self):
        qs = Product.objects.filter(is_active=True).select_related("process", "material", "option")
        params = self.request.query_params
        if params.get("process"):
            qs = qs.filter(process__slug=params["process"])
        if params.get("material"):
            qs = qs.filter(material__slug=params["material"])
        if params.get("q"):
            q = params["q"].strip()
            qs = qs.filter(Q(title__icontains=q) | Q(description__icontains=q))
        sort = params.get("sort", "newest")
        if sort == "price_asc":
            qs = qs.order_by("price_from")
        elif sort == "price_desc":
            qs = qs.order_by("-price_from")
        elif sort == "popular":
            qs = qs.order_by("-is_orderable", "-created_at")
        else:
            qs = qs.order_by("-created_at")
        return qs


class ProductDetailView(RetrieveAPIView):
    serializer_class = ProductDetailSerializer
    permission_classes = [AllowAny]
    lookup_field = "slug"
    queryset = Product.objects.filter(is_active=True).select_related("process", "material", "option").prefetch_related("images")
