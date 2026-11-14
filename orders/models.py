from django.conf import settings
from django.core.validators import FileExtensionValidator
from django.db import models

STATUS_CHOICES = [
    ("received", "received"),
    ("reviewing", "reviewing"),
    ("quoted", "quoted"),
    ("confirmed", "confirmed"),
    ("in_production", "in_production"),
    ("finishing", "finishing"),
    ("quality_check", "quality_check"),
    ("ready_or_shipped", "ready_or_shipped"),
    ("delivered", "delivered"),
    ("cancelled", "cancelled"),
]

ALLOWED_FILE_EXTENSIONS = ["stl", "3mf", "obj", "step", "stp", "iges", "igs", "dxf", "jpg", "png", "pdf"]


def request_file_upload_to(instance, filename):
    return f"requests/{instance.request_id}/{filename}"


class CustomRequest(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="custom_requests")
    title = models.CharField(max_length=200)
    process = models.ForeignKey("catalog.Process", on_delete=models.PROTECT, related_name="custom_requests")
    material = models.ForeignKey(
        "catalog.Material", on_delete=models.SET_NULL, null=True, blank=True, related_name="custom_requests"
    )
    color = models.CharField(max_length=50, blank=True)
    quantity = models.IntegerField(default=1)
    dimensions_text = models.CharField(max_length=200, blank=True)
    finish = models.CharField(max_length=100, blank=True)
    deadline = models.DateField(null=True, blank=True)
    budget_min = models.IntegerField(null=True, blank=True, help_text="Toman")
    budget_max = models.IntegerField(null=True, blank=True, help_text="Toman")
    intended_use = models.TextField(blank=True)
    notes = models.TextField(blank=True)
    showcase_item = models.ForeignKey(
        "catalog.ShowcaseItem", on_delete=models.SET_NULL, null=True, blank=True, related_name="custom_requests"
    )
    status = models.CharField(max_length=30, choices=STATUS_CHOICES, default="received")
    estimate_min = models.IntegerField(null=True, blank=True, help_text="Toman")
    estimate_max = models.IntegerField(null=True, blank=True, help_text="Toman")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("-created_at",)

    def __str__(self):
        return f"#{self.id} {self.title}"


class RequestFile(models.Model):
    request = models.ForeignKey(CustomRequest, on_delete=models.CASCADE, related_name="files")
    file = models.FileField(
        upload_to=request_file_upload_to,
        validators=[FileExtensionValidator(allowed_extensions=ALLOWED_FILE_EXTENSIONS)],
    )
    original_name = models.CharField(max_length=255)
    file_type = models.CharField(max_length=20)
    size_bytes = models.BigIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.original_name


class RequestMessage(models.Model):
    request = models.ForeignKey(CustomRequest, on_delete=models.CASCADE, related_name="messages")
    author = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="request_messages")
    body = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("created_at",)


class Quote(models.Model):
    STATUS_CHOICES = [
        ("draft", "draft"),
        ("sent", "sent"),
        ("accepted", "accepted"),
        ("rejected", "rejected"),
        ("expired", "expired"),
    ]

    custom_request = models.ForeignKey(CustomRequest, on_delete=models.CASCADE, related_name="quotes")
    price = models.IntegerField(help_text="Toman")
    lead_time_days = models.IntegerField()
    message = models.TextField(blank=True)
    valid_until = models.DateField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="draft")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("-created_at",)

    def __str__(self):
        return f"quote for request #{self.custom_request_id}"

    @property
    def is_expired(self):
        from django.utils import timezone

        if self.status in ("expired", "accepted", "rejected"):
            return self.status == "expired"
        if not self.valid_until:
            return True
        return timezone.localdate() > self.valid_until


class Order(models.Model):
    PAYMENT_CHOICES = [
        ("unpaid", "unpaid"),
        ("paid", "paid"),
        ("failed", "failed"),
        ("refunded", "refunded"),
    ]

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="orders")
    custom_request = models.ForeignKey(
        CustomRequest, on_delete=models.SET_NULL, null=True, blank=True, related_name="orders"
    )
    product = models.ForeignKey("catalog.Product", on_delete=models.SET_NULL, null=True, blank=True, related_name="orders")
    quote = models.OneToOneField(Quote, on_delete=models.SET_NULL, null=True, blank=True, related_name="order")
    total = models.IntegerField(help_text="Toman")
    status = models.CharField(max_length=30, choices=STATUS_CHOICES, default="quoted")
    payment_status = models.CharField(max_length=20, choices=PAYMENT_CHOICES, default="unpaid")
    shipping_method = models.CharField(max_length=20, choices=[("pickup", "pickup"), ("delivery", "delivery")], default="pickup")
    address = models.TextField(blank=True)
    tracking_note = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("-created_at",)

    def __str__(self):
        return f"order #{self.id}"
