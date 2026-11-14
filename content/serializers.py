from rest_framework import serializers

from .models import BlogPost, ContactMessage, SiteSetting


class BlogPostListSerializer(serializers.ModelSerializer):
    class Meta:
        model = BlogPost
        fields = ("id", "title", "slug", "summary", "cover", "category", "published_at")


class BlogPostDetailSerializer(BlogPostListSerializer):
    class Meta(BlogPostListSerializer.Meta):
        fields = BlogPostListSerializer.Meta.fields + ("body", "updated_at")


class SiteSettingSerializer(serializers.ModelSerializer):
    class Meta:
        model = SiteSetting
        fields = (
            "site_name", "logo", "accent_color", "contact_email", "phone",
            "address", "working_hours", "expected_reply_text",
        )


class ContactMessageSerializer(serializers.ModelSerializer):
    class Meta:
        model = ContactMessage
        fields = ("id", "name", "email", "phone", "subject", "body", "created_at")
        read_only_fields = ("id", "created_at")
