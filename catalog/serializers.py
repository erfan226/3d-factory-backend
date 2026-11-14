from rest_framework import serializers

from .models import (
    Category,
    CollectionItem,
    Comment,
    Material,
    Make,
    Process,
    Product,
    ProductImage,
    ProductOption,
    ShowcaseFile,
    ShowcaseImage,
    ShowcaseItem,
    Tag,
    UserCollection,
)


class ProcessSerializer(serializers.ModelSerializer):
    class Meta:
        model = Process
        fields = ("id", "name", "slug", "description", "quote_type", "needs_drawing", "is_active", "sort_order")


class MaterialSerializer(serializers.ModelSerializer):
    process = serializers.SlugRelatedField(slug_field="slug", read_only=True)

    class Meta:
        model = Material
        fields = ("id", "process", "name", "slug", "colors", "price_tier", "description", "is_active")


class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = ("id", "name", "slug", "parent", "sort_order")


class TagSerializer(serializers.ModelSerializer):
    class Meta:
        model = Tag
        fields = ("id", "name", "slug")


class ShowcaseFileSerializer(serializers.ModelSerializer):
    file = serializers.SerializerMethodField()

    class Meta:
        model = ShowcaseFile
        fields = ("id", "original_name", "file", "file_type", "size_bytes", "is_preview_model")

    def get_file(self, obj):
        return obj.file.url if obj.file else ""


class ShowcaseImageSerializer(serializers.ModelSerializer):
    class Meta:
        model = ShowcaseImage
        fields = ("id", "image", "sort_order")


class ShowcaseItemCardSerializer(serializers.ModelSerializer):
    """Compact serializer for grids and related items."""

    cover = serializers.SerializerMethodField()
    likes_count = serializers.IntegerField(read_only=True, default=0)
    downloads_count = serializers.IntegerField(read_only=True, default=0)
    makes_count = serializers.IntegerField(read_only=True, default=0)
    comments_count = serializers.IntegerField(read_only=True, default=0)
    category = serializers.SlugRelatedField(slug_field="slug", read_only=True)
    process = serializers.SlugRelatedField(slug_field="slug", read_only=True)
    material = MaterialSerializer(read_only=True)

    class Meta:
        model = ShowcaseItem
        fields = (
            "id", "title", "slug", "summary", "cover", "category", "process", "material",
            "license", "allow_download", "is_featured", "likes_count", "downloads_count",
            "makes_count", "comments_count", "created_at",
        )

    def get_cover(self, obj):
        return obj.cover_url


class CommentSerializer(serializers.ModelSerializer):
    user = serializers.SerializerMethodField()

    class Meta:
        model = Comment
        fields = ("id", "user", "body", "is_visible", "created_at")
        read_only_fields = ("id", "is_visible", "created_at")

    def get_user(self, obj):
        return {"id": obj.user_id, "name": obj.user.get_full_name() or obj.user.email}


class MakeSerializer(serializers.ModelSerializer):
    user = serializers.SerializerMethodField()
    photo = serializers.ImageField(required=True)

    class Meta:
        model = Make
        fields = ("id", "user", "photo", "note", "print_settings", "created_at")
        read_only_fields = ("id", "created_at")

    def get_user(self, obj):
        return {"id": obj.user_id, "name": obj.user.get_full_name() or obj.user.email}


class ShowcaseItemDetailSerializer(ShowcaseItemCardSerializer):
    tags = TagSerializer(many=True, read_only=True)
    files = serializers.SerializerMethodField()
    images = serializers.SerializerMethodField()
    remixes = serializers.SerializerMethodField()
    remixed_from = serializers.SerializerMethodField()

    class Meta(ShowcaseItemCardSerializer.Meta):
        fields = ShowcaseItemCardSerializer.Meta.fields + (
            "description", "tags", "files", "images", "remixed_from", "remixes", "updated_at",
        )

    def get_files(self, obj):
        return ShowcaseFileSerializer(obj.files.all(), many=True).data

    def get_images(self, obj):
        return ShowcaseImageSerializer(obj.images.all(), many=True).data

    def get_remixes(self, obj):
        remixes = obj.remixes.filter(is_active=True)[:6]
        return ShowcaseItemCardSerializer(remixes, many=True).data

    def get_remixed_from(self, obj):
        if obj.remixed_from_id and obj.remixed_from.is_active:
            return {"slug": obj.remixed_from.slug, "title": obj.remixed_from.title}
        return None


class ShowcaseItemPublishValidator:
    """Publish requires at least one model file and one image."""

    MODEL_TYPES = {"stl", "3mf", "obj", "step", "stp", "iges", "igs", "glb", "gltf"}

    @staticmethod
    def validate_publishable(item: ShowcaseItem):
        from config.messages import NO_IMAGE, NO_MODEL_FILE
        from rest_framework.exceptions import APIException

        class PublishError(APIException):
            status_code = 400

        has_model = item.files.filter(file_type__in=ShowcaseItemPublishValidator.MODEL_TYPES).exists()
        has_image = item.images.exists() or bool(item.cover_image)
        if not has_model:
            raise PublishError({"detail": "برای انتشار حداقل یک فایل مدل لازم است.", "code": NO_MODEL_FILE})
        if not has_image:
            raise PublishError({"detail": "برای انتشار حداقل یک تصویر لازم است.", "code": NO_IMAGE})


class UserCollectionSerializer(serializers.ModelSerializer):
    item_count = serializers.IntegerField(read_only=True, default=0)

    class Meta:
        model = UserCollection
        fields = ("id", "name", "description", "is_public", "item_count", "created_at")
        read_only_fields = ("id", "created_at")

    def validate_name(self, value):
        if not value.strip():
            raise serializers.ValidationError("This field may not be blank.")
        return value.strip()


class ProductImageSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProductImage
        fields = ("id", "image", "sort_order")


class ProductOptionSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProductOption
        fields = ("id", "name", "values", "price_delta")


class ProductCardSerializer(serializers.ModelSerializer):
    cover = serializers.SerializerMethodField()
    process = serializers.SlugRelatedField(slug_field="slug", read_only=True)
    material = MaterialSerializer(read_only=True)
    price_from = serializers.IntegerField(read_only=True)

    class Meta:
        model = Product
        fields = (
            "id", "title", "slug", "description", "cover", "process", "material",
            "price_from", "lead_time_days", "is_orderable", "is_active", "created_at",
        )

    def get_cover(self, obj):
        return obj.cover_url


class ProductDetailSerializer(ProductCardSerializer):
    images = ProductImageSerializer(many=True, read_only=True)
    option = ProductOptionSerializer(read_only=True)
    showcase_item = serializers.SerializerMethodField()

    class Meta(ProductCardSerializer.Meta):
        fields = ProductCardSerializer.Meta.fields + ("images", "option", "showcase_item")

    def get_showcase_item(self, obj):
        if obj.showcase_item_id and obj.showcase_item.is_active:
            return {"slug": obj.showcase_item.slug, "title": obj.showcase_item.title}
        return None


class CollectionItemSerializer(serializers.ModelSerializer):
    item = ShowcaseItemCardSerializer(read_only=True)

    class Meta:
        model = CollectionItem
        fields = ("id", "item", "created_at")
