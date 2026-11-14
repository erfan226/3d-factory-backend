from django.contrib import admin

from .models import Payment


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ("id", "order", "provider", "amount_toman", "amount_rial", "status", "ref_id", "authority", "created_at")
    list_filter = ("status", "provider")
    search_fields = ("authority", "ref_id", "order__user__email")
    readonly_fields = ("raw_response",)
