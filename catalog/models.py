from django.conf import settings
from django.db import models


class Process(models.Model):
    QUOTE_MANUAL = "manual"
    QUOTE_ESTIMATE = "estimate"
    QUOTE_TYPE_CHOICES = [(QUOTE_MANUAL, "manual"), (QUOTE_ESTIMATE, "estimate")]

    name = models.CharField(max_length=100, unique=True)
    slug = models.SlugField(unique=True)
    description = models.TextField(blank=True)
    quote_type = models.CharField(max_length=20, choices=QUOTE_TYPE_CHOICES, default=QUOTE_MANUAL)
    needs_drawing = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    sort_order = models.IntegerField(default=0)

    class Meta:
        ordering = ("sort_order", "name")

    def __str__(self):
        return self.name


class Material(models.Model):
    PRICE_LOW = "low"
    PRICE_MEDIUM = "medium"
    PRICE_HIGH = "high"
    PRICE_TIER_CHOICES = [(PRICE_LOW, "low"), (PRICE_MEDIUM, "medium"), (PRICE_HIGH, "high")]

    process = models.ForeignKey(Process, on_delete=models.CASCADE, related_name="materials")
    name = models.CharField(max_length=100)
    slug = models.SlugField(unique=True)
    colors = models.JSONField(default=list, blank=True)
    price_tier = models.CharField(max_length=20, choices=PRICE_TIER_CHOICES, default=PRICE_MEDIUM)
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ("name",)

    def __str__(self):
        return self.name


class Category(models.Model):
    name = models.CharField(max_length=100, unique=True)
    slug = models.SlugField(unique=True)
    parent = models.ForeignKey("self", on_delete=models.SET_NULL, null=True, blank=True, related_name="children")
    sort_order = models.IntegerField(default=0)

    class Meta:
        ordering = ("sort_order", "name")
        verbose_name_plural = "categories"

    def __str__(self):
        return self.name


class Tag(models.Model):
    name = models.CharField(max_length=50, unique=True)
    slug = models.SlugField(unique=True)

    class Meta:
        ordering = ("name",)

    def __str__(self):
        return self.name


class ShowcaseItem(models.Model):
    LICENSE_CC_BY = "cc-by"
    LICENSE_CC_BY_SA = "cc-by-sa"
    LICENSE_CC_BY_NC = "cc-by-nc"
    LICENSE_CC_BY_NC_SA = "cc-by-nc-sa"
    LICENSE_FACTORY_ONLY = "factory-only"
    LICENSE_CHOICES = [
        (LICENSE_CC_BY, "CC BY"),
        (LICENSE_CC_BY_SA, "CC BY-SA"),
        (LICENSE_CC_BY_NC, "CC BY-NC"),
        (LICENSE_CC_BY_NC_SA, "CC BY-NC-SA"),
        (LICENSE_FACTORY_ONLY, "factory-only"),
    ]

    title = models.CharField(max_length=200)
    slug = models.SlugField(unique=True)
    summary = models.TextField()
    description = models.TextField()
    category = models.ForeignKey(Category, on_delete=models.SET_NULL, null=True, blank=True, related_name="items")
    tags = models.ManyToManyField(Tag, blank=True, related_name="items")
    process = models.ForeignKey(Process, on_delete=models.SET_NULL, null=True, blank=True, related_name="items")
    material = models.ForeignKey(Material, on_delete=models.SET_NULL, null=True, blank=True, related_name="items")
    license = models.CharField(max_length=20, choices=LICENSE_CHOICES, default=LICENSE_FACTORY_ONLY)
    allow_download = models.BooleanField(default=False)
    remixed_from = models.ForeignKey("self", on_delete=models.SET_NULL, null=True, blank=True, related_name="remixes")
    is_featured = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    cover_image = models.ImageField(upload_to="showcase/covers/", blank=True)
    admin_note = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("-created_at",)

    def __str__(self):
        return self.title

    @property
    def first_image(self):
        return self.images.order_by("sort_order", "id").first()

    @property
    def cover_url(self):
        """Cover: explicit cover_image wins, else first gallery image."""
        if self.cover_image:
            return self.cover_image.url
        image = self.first_image
        return image.image.url if image else ""


class ShowcaseFile(models.Model):
    item = models.ForeignKey(ShowcaseItem, on_delete=models.CASCADE, related_name="files")
    file = models.FileField(upload_to="showcase/files/")
    original_name = models.CharField(max_length=255)
    file_type = models.CharField(max_length=20)
    size_bytes = models.BigIntegerField(default=0)
    is_preview_model = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.original_name


class ShowcaseImage(models.Model):
    item = models.ForeignKey(ShowcaseItem, on_delete=models.CASCADE, related_name="images")
    image = models.ImageField(upload_to="showcase/images/")
    sort_order = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("sort_order", "id")

    def __str__(self):
        return f"image {self.sort_order} of {self.item_id}"


class DownloadLog(models.Model):
    """One row per download so downloads_count stays a computed annotation."""

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="downloads"
    )
    item = models.ForeignKey(ShowcaseItem, on_delete=models.CASCADE, related_name="download_logs")
    file = models.ForeignKey(ShowcaseFile, on_delete=models.SET_NULL, null=True, blank=True)
    is_zip = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)


class Like(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="likes")
    item = models.ForeignKey(ShowcaseItem, on_delete=models.CASCADE, related_name="likes")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=("user", "item"), name="unique_like")]


class UserCollection(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="collections")
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    is_public = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("-created_at",)

    def __str__(self):
        return self.name


class CollectionItem(models.Model):
    collection = models.ForeignKey(UserCollection, on_delete=models.CASCADE, related_name="items")
    item = models.ForeignKey(ShowcaseItem, on_delete=models.CASCADE, related_name="collection_items")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=("collection", "item"), name="unique_collection_item")]


class Comment(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="comments")
    item = models.ForeignKey(ShowcaseItem, on_delete=models.CASCADE, related_name="comments")
    body = models.TextField(max_length=2000)
    is_visible = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("-created_at",)

    def __str__(self):
        return f"comment by {self.user_id} on {self.item_id}"


class Make(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="makes")
    item = models.ForeignKey(ShowcaseItem, on_delete=models.CASCADE, related_name="makes")
    photo = models.ImageField(upload_to="makes/")
    note = models.TextField(blank=True)
    print_settings = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("-created_at",)


class Product(models.Model):
    title = models.CharField(max_length=200)
    slug = models.SlugField(unique=True)
    description = models.TextField()
    showcase_item = models.ForeignKey(
        ShowcaseItem, on_delete=models.SET_NULL, null=True, blank=True, related_name="products"
    )
    process = models.ForeignKey(Process, on_delete=models.PROTECT, related_name="products")
    material = models.ForeignKey(Material, on_delete=models.PROTECT, related_name="products")
    price_from = models.IntegerField(help_text="Toman")
    lead_time_days = models.IntegerField(default=3)
    is_orderable = models.BooleanField(default=True)
    is_active = models.BooleanField(default=True)
    cover_image = models.ImageField(upload_to="products/covers/", blank=True)
    admin_note = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("-created_at",)

    def __str__(self):
        return self.title

    @property
    def cover_url(self):
        if self.cover_image:
            return self.cover_image.url
        image = self.images.order_by("sort_order", "id").first()
        return image.image.url if image else ""


class ProductImage(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="images")
    image = models.ImageField(upload_to="products/images/")
    sort_order = models.IntegerField(default=0)

    class Meta:
        ordering = ("sort_order", "id")


class ProductOption(models.Model):
    product = models.OneToOneField(Product, on_delete=models.CASCADE, related_name="option")
    name = models.CharField(max_length=100)
    values = models.JSONField(default=list)
    price_delta = models.JSONField(default=list, help_text="Delta per value, same order as values, in Toman")
