from django.db import models


class BlogPost(models.Model):
    title = models.CharField(max_length=200)
    slug = models.SlugField(unique=True)
    summary = models.TextField()
    body = models.TextField()
    cover = models.ImageField(upload_to="blog/", null=True, blank=True)
    category = models.CharField(max_length=100, blank=True)
    is_published = models.BooleanField(default=False)
    published_at = models.DateTimeField(null=True, blank=True)
    admin_note = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("-published_at", "-created_at")

    def __str__(self):
        return self.title


class SiteSetting(models.Model):
    site_name = models.CharField(max_length=100, default="کارگاه سه‌بعدی")
    logo = models.ImageField(upload_to="site/", null=True, blank=True)
    accent_color = models.CharField(max_length=20, default="#9B7665")
    contact_email = models.EmailField(blank=True)
    phone = models.CharField(max_length=30, blank=True)
    address = models.TextField(blank=True)
    working_hours = models.CharField(max_length=200, blank=True)
    expected_reply_text = models.TextField(
        blank=True,
        help_text="Text shown after a custom request is submitted.",
    )

    class Meta:
        verbose_name = "site setting"
        verbose_name_plural = "site setting (single row)"

    def __str__(self):
        return self.site_name

    def save(self, *args, **kwargs):
        # Singleton: never allow a second row.
        self.pk = 1
        super().save(*args, **kwargs)

    @classmethod
    def load(cls):
        obj, _ = cls.objects.get_or_create(pk=1)
        return obj

    def delete(self, *args, **kwargs):
        pass


class ContactMessage(models.Model):
    name = models.CharField(max_length=150)
    email = models.EmailField()
    phone = models.CharField(max_length=30, blank=True)
    subject = models.CharField(max_length=200)
    body = models.TextField()
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("-created_at",)

    def __str__(self):
        return f"{self.subject} - {self.name}"
