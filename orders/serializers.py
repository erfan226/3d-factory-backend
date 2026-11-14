from django.conf import settings
from django.core.files.base import File
from rest_framework import serializers

from catalog.models import Material, Process, ShowcaseItem
from config import messages as msgs

from .models import ALLOWED_FILE_EXTENSIONS, CustomRequest, Order, Quote, RequestFile, RequestMessage


class RequestFileSerializer(serializers.ModelSerializer):
    class Meta:
        model = RequestFile
        fields = ("id", "original_name", "file_type", "size_bytes", "created_at")


class RequestMessageSerializer(serializers.ModelSerializer):
    author = serializers.SerializerMethodField()

    class Meta:
        model = RequestMessage
        fields = ("id", "author", "body", "created_at")
        read_only_fields = ("id", "created_at")

    def get_author(self, obj):
        name = obj.author.get_full_name() or obj.author.email
        return {"id": obj.author_id, "name": name, "is_staff": obj.author.is_staff}


class QuoteSerializer(serializers.ModelSerializer):
    class Meta:
        model = Quote
        fields = ("id", "price", "lead_time_days", "message", "valid_until", "status", "created_at")
        read_only_fields = ("id", "created_at")


class CustomRequestListSerializer(serializers.ModelSerializer):
    process = serializers.SlugRelatedField(slug_field="slug", read_only=True)
    material = serializers.SlugRelatedField(slug_field="slug", read_only=True)
    file_count = serializers.SerializerMethodField()
    has_quote = serializers.SerializerMethodField()

    class Meta:
        model = CustomRequest
        fields = (
            "id", "title", "process", "material", "status", "quantity", "created_at",
            "updated_at", "estimate_min", "estimate_max", "file_count", "has_quote",
        )

    def get_file_count(self, obj):
        return obj.files.count()

    def get_has_quote(self, obj):
        return obj.quotes.filter(status__in=["draft", "sent"]).exists()


class CustomRequestDetailSerializer(serializers.ModelSerializer):
    process = serializers.SlugRelatedField(slug_field="slug", read_only=True)
    material = serializers.SlugRelatedField(slug_field="slug", read_only=True)
    showcase_item = serializers.SerializerMethodField()
    files = RequestFileSerializer(many=True, read_only=True)
    messages = RequestMessageSerializer(many=True, read_only=True)
    quote = serializers.SerializerMethodField()

    class Meta:
        model = CustomRequest
        fields = (
            "id", "title", "process", "material", "color", "quantity", "dimensions_text",
            "finish", "deadline", "budget_min", "budget_max", "intended_use", "notes",
            "showcase_item", "status", "estimate_min", "estimate_max", "files", "messages",
            "quote", "created_at", "updated_at",
        )

    def get_showcase_item(self, obj):
        if obj.showcase_item_id:
            return {"slug": obj.showcase_item.slug, "title": obj.showcase_item.title}
        return None

    def get_quote(self, obj):
        quote = obj.quotes.order_by("-created_at").first()
        return QuoteSerializer(quote).data if quote else None


class CustomRequestCreateSerializer(serializers.ModelSerializer):
    """Multipart create with server-side validation of files, types, sizes, counts."""

    files = serializers.ListField(
        child=serializers.FileField(), write_only=True, required=False, allow_empty=True
    )
    process = serializers.SlugRelatedField(slug_field="slug", queryset=Process.objects.all())
    material = serializers.SlugRelatedField(
        slug_field="slug", queryset=Material.objects.all(), allow_null=True, required=False
    )
    showcase_item = serializers.SlugRelatedField(
        slug_field="slug", queryset=ShowcaseItem.objects.all(), allow_null=True, required=False
    )

    class Meta:
        model = CustomRequest
        fields = (
            "id", "title", "process", "material", "color", "quantity", "dimensions_text",
            "finish", "deadline", "budget_min", "budget_max", "intended_use", "notes",
            "showcase_item", "files",
        )
        read_only_fields = ("id",)

    def validate_title(self, value):
        if not value.strip():
            raise serializers.ValidationError("This field may not be blank.")
        return value.strip()

    def validate_process(self, value):
        if not value.is_active:
            raise serializers.ValidationError("This process is not active.")
        return value

    def validate_quantity(self, value):
        if value < 1:
            raise serializers.ValidationError("A valid integer is required.")
        return value

    def validate_files(self, uploaded_files):
        max_files = settings.MAX_FILES_PER_REQUEST
        max_size = settings.MAX_UPLOAD_SIZE_BYTES
        if len(uploaded_files) > max_files:
            raise serializers.ValidationError(
                {"detail": msgs.PERSIAN_ERRORS[msgs.TOO_MANY_FILES], "code": msgs.TOO_MANY_FILES}
            )
        for uploaded in uploaded_files:
            ext = uploaded.name.rsplit(".", 1)[-1].lower() if "." in uploaded.name else ""
            if ext not in ALLOWED_FILE_EXTENSIONS:
                raise serializers.ValidationError(
                    {
                        "detail": f"{msgs.PERSIAN_ERRORS[msgs.INVALID_FILE_TYPE]} ({uploaded.name})",
                        "code": msgs.INVALID_FILE_TYPE,
                    }
                )
            if uploaded.size > max_size:
                raise serializers.ValidationError(
                    {
                        "detail": f"{msgs.PERSIAN_ERRORS[msgs.FILE_TOO_LARGE]} ({uploaded.name})",
                        "code": msgs.FILE_TOO_LARGE,
                    }
                )
        return uploaded_files

    def validate(self, attrs):
        """No model/CAD files allowed only when at least one image and dimensions are present."""
        files = attrs.get("files") or []
        has_model = any(
            f.name.rsplit(".", 1)[-1].lower() not in ("jpg", "png", "pdf") for f in files
        )
        has_image = any(f.name.rsplit(".", 1)[-1].lower() in ("jpg", "png") for f in files)
        has_dimensions = bool((attrs.get("dimensions_text") or "").strip())
        if not has_model and not (has_image and has_dimensions):
            raise serializers.ValidationError(
                {
                    "detail": "بدون فایل مدل، ارسال حداقل یک تصویر و مشخصات ابعادی الزامی است.",
                    "code": msgs.VALIDATION_ERROR,
                }
            )
        return attrs

    def create(self, validated_data):
        uploaded_files = validated_data.pop("files", [])
        request = CustomRequest.objects.create(user=self.context["request"].user, **validated_data)
        for uploaded in uploaded_files:
            ext = uploaded.name.rsplit(".", 1)[-1].lower()
            RequestFile.objects.create(
                request=request,
                file=File(uploaded),
                original_name=uploaded.name[:255],
                file_type=ext,
                size_bytes=uploaded.size,
            )
        return request


class OrderSerializer(serializers.ModelSerializer):
    custom_request = serializers.SerializerMethodField()
    product = serializers.SerializerMethodField()
    quote = QuoteSerializer(read_only=True)

    class Meta:
        model = Order
        fields = (
            "id", "custom_request", "product", "quote", "total", "status", "payment_status",
            "shipping_method", "address", "tracking_note", "created_at", "updated_at",
        )

    def get_custom_request(self, obj):
        if obj.custom_request_id:
            return {"id": obj.custom_request_id, "title": obj.custom_request.title}
        return None

    def get_product(self, obj):
        if obj.product_id:
            return {"slug": obj.product.slug, "title": obj.product.title}
        return None
