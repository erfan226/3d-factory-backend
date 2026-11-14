from django import forms
from django.contrib import admin

from config.messages import NO_IMAGE, NO_MODEL_FILE

from .models import (
    Category,
    CollectionItem,
    Comment,
    DownloadLog,
    Like,
    Make,
    Material,
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


@admin.register(Process)
class ProcessAdmin(admin.ModelAdmin):
    list_display = ("name", "slug", "quote_type", "needs_drawing", "is_active", "sort_order")
    list_editable = ("is_active", "sort_order", "needs_drawing")
    list_filter = ("is_active", "quote_type", "needs_drawing")
    search_fields = ("name", "slug")


@admin.register(Material)
class MaterialAdmin(admin.ModelAdmin):
    list_display = ("name", "slug", "process", "price_tier", "is_active")
    list_editable = ("is_active",)
    list_filter = ("is_active", "process", "price_tier")
    search_fields = ("name", "slug")


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ("name", "slug", "parent", "sort_order")
    list_editable = ("sort_order",)
    search_fields = ("name", "slug")


@admin.register(Tag)
class TagAdmin(admin.ModelAdmin):
    list_display = ("name", "slug")
    search_fields = ("name", "slug")


class ShowcaseFileInline(admin.TabularInline):
    model = ShowcaseFile
    extra = 0
    fields = ("file", "original_name", "file_type", "size_bytes", "is_preview_model")
    readonly_fields = ("original_name", "file_type", "size_bytes")


class ShowcaseImageInline(admin.TabularInline):
    model = ShowcaseImage
    extra = 0
    fields = ("image", "sort_order")


class ShowcaseItemAdminForm(forms.ModelForm):
    class Meta:
        model = ShowcaseItem
        fields = "__all__"

    def clean(self):
        cleaned = super().clean()
        if cleaned.get("is_active"):
            item = self.instance
            model_types = {"stl", "3mf", "obj", "step", "stp", "iges", "igs", "glb", "gltf"}
            has_model = item.pk and item.files.filter(file_type__in=model_types).exists()
            has_image = item.images.exists() or cleaned.get("cover_image")
            if not has_model:
                self.add_error(None, f"{NO_MODEL_FILE}: برای انتشار حداقل یک فایل مدل لازم است.")
            if not has_image:
                self.add_error(None, f"{NO_IMAGE}: برای انتشار حداقل یک تصویر لازم است.")
        return cleaned


@admin.register(ShowcaseItem)
class ShowcaseItemAdmin(admin.ModelAdmin):
    form = ShowcaseItemAdminForm
    list_display = ("title", "slug", "category", "process", "is_featured", "is_active", "created_at")
    list_filter = ("is_active", "is_featured", "category", "process", "license")
    search_fields = ("title", "summary", "slug")
    filter_horizontal = ("tags",)
    readonly_fields = ("admin_note",)
    inlines = [ShowcaseFileInline, ShowcaseImageInline]


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ("title", "slug", "process", "price_from", "lead_time_days", "is_orderable", "is_active")
    list_filter = ("is_active", "is_orderable", "process", "material")
    search_fields = ("title", "slug")


@admin.register(ProductImage)
class ProductImageAdmin(admin.ModelAdmin):
    list_display = ("product", "sort_order")


@admin.register(ProductOption)
class ProductOptionAdmin(admin.ModelAdmin):
    list_display = ("product", "name")


@admin.register(Like)
class LikeAdmin(admin.ModelAdmin):
    list_display = ("user", "item", "created_at")
    search_fields = ("user__email", "item__title")


@admin.register(UserCollection)
class UserCollectionAdmin(admin.ModelAdmin):
    list_display = ("name", "user", "is_public", "created_at")
    list_filter = ("is_public",)
    search_fields = ("name", "user__email")


@admin.register(CollectionItem)
class CollectionItemAdmin(admin.ModelAdmin):
    list_display = ("collection", "item", "created_at")


@admin.register(Comment)
class CommentAdmin(admin.ModelAdmin):
    list_display = ("user", "item", "is_visible", "created_at")
    list_filter = ("is_visible",)
    search_fields = ("body", "user__email")
    list_editable = ("is_visible",)


@admin.register(Make)
class MakeAdmin(admin.ModelAdmin):
    list_display = ("user", "item", "created_at")
    search_fields = ("user__email", "item__title")


@admin.register(DownloadLog)
class DownloadLogAdmin(admin.ModelAdmin):
    list_display = ("item", "user", "file", "is_zip", "created_at")
    list_filter = ("is_zip",)
