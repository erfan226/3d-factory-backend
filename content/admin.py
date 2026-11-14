from django import forms
from django.contrib import admin
from django.utils.text import slugify

from .models import BlogPost, ContactMessage, SiteSetting


class SiteSettingAdminForm(forms.ModelForm):
    class Meta:
        model = SiteSetting
        fields = "__all__"


@admin.register(SiteSetting)
class SiteSettingAdmin(admin.ModelAdmin):
    """Singleton: one row only."""

    form = SiteSettingAdminForm
    list_display = ("site_name", "contact_email", "phone", "accent_color")

    def has_add_permission(self, request):
        return not SiteSetting.objects.exists()

    def has_delete_permission(self, request, obj=None):
        return False

    def get_queryset(self, request):
        SiteSetting.load()
        return super().get_queryset(request)


@admin.register(BlogPost)
class BlogPostAdmin(admin.ModelAdmin):
    list_display = ("title", "slug", "category", "is_published", "published_at")
    list_filter = ("is_published", "category")
    search_fields = ("title", "summary", "body")
    prepopulated_fields = {"slug": ("title",)}
    list_editable = ("is_published",)

    def save_model(self, request, obj, form, change):
        if not obj.slug and obj.title:
            base = slugify(obj.title, allow_unicode=True) or f"post-{BlogPost.objects.count() + 1}"
            slug, i = base, 1
            while BlogPost.objects.filter(slug=slug).exclude(pk=obj.pk).exists():
                i += 1
                slug = f"{base}-{i}"
            obj.slug = slug
        if obj.is_published and not obj.published_at:
            from django.utils import timezone

            obj.published_at = timezone.now()
        super().save_model(request, obj, form, change)


@admin.register(ContactMessage)
class ContactMessageAdmin(admin.ModelAdmin):
    list_display = ("name", "email", "phone", "subject", "is_read", "created_at")
    list_filter = ("is_read",)
    search_fields = ("name", "email", "subject", "body")
    list_editable = ("is_read",)
