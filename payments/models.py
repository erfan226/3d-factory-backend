from django.conf import settings
from django.db import models


class Payment(models.Model):
    STATUS_CHOICES = [
        ("created", "created"),
        ("paid", "paid"),
        ("failed", "failed"),
        ("cancelled", "cancelled"),
    ]

    order = models.ForeignKey("orders.Order", on_delete=models.CASCADE, related_name="payments")
    provider = models.CharField(max_length=30, default="zarinpal")
    authority = models.CharField(max_length=100, unique=True)
    ref_id = models.CharField(max_length=100, blank=True)
    amount_rial = models.IntegerField()
    amount_toman = models.IntegerField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="created")
    raw_response = models.JSONField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("-created_at",)

    def __str__(self):
        return f"payment for order #{self.order_id} ({self.status})"
