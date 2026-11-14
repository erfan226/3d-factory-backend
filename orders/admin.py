from django.contrib import admin
from django.utils import timezone

from .models import CustomRequest, Order, Quote, RequestFile, RequestMessage

STATUS_ORDER = [
    "received", "reviewing", "quoted", "confirmed", "in_production",
    "finishing", "quality_check", "ready_or_shipped", "delivered", "cancelled",
]


class RequestFileInline(admin.TabularInline):
    model = RequestFile
    extra = 0
    readonly_fields = ("original_name", "file_type", "size_bytes", "created_at")
    fields = ("file", "original_name", "file_type", "size_bytes", "created_at")


class RequestMessageInline(admin.TabularInline):
    model = RequestMessage
    extra = 0
    readonly_fields = ("author", "body", "created_at")
    fields = ("author", "body", "created_at")
    can_delete = False


class QuoteInline(admin.StackedInline):
    model = Quote
    extra = 0
    fields = ("price", "lead_time_days", "message", "valid_until", "status")


@admin.register(CustomRequest)
class CustomRequestAdmin(admin.ModelAdmin):
    list_display = ("id", "title", "user", "process", "status", "quantity", "created_at")
    list_filter = ("status", "process")
    search_fields = ("title", "user__email", "notes")
    readonly_fields = ("created_at", "updated_at")
    inlines = [RequestFileInline, RequestMessageInline, QuoteInline]

    actions = ["mark_reviewing", "advance_status", "mark_cancelled"]

    @admin.action(description="Move to next production status")
    def advance_status(self, request, queryset):
        for obj in queryset:
            current = STATUS_ORDER.index(obj.status) if obj.status in STATUS_ORDER else 0
            if obj.status != "cancelled" and current < STATUS_ORDER.index("delivered"):
                obj.status = STATUS_ORDER[current + 1]
                obj.save(update_fields=["status", "updated_at"])

    @admin.action(description="Mark as reviewing")
    def mark_reviewing(self, request, queryset):
        queryset.update(status="reviewing")

    @admin.action(description="Mark as cancelled")
    def mark_cancelled(self, request, queryset):
        queryset.update(status="cancelled")


@admin.register(Quote)
class QuoteAdmin(admin.ModelAdmin):
    list_display = ("id", "custom_request", "price", "lead_time_days", "valid_until", "status", "is_stale")
    list_filter = ("status",)
    search_fields = ("custom_request__title", "custom_request__user__email")
    actions = ["mark_expired", "mark_sent"]

    @admin.display(boolean=True, description="past valid_until")
    def is_stale(self, obj):
        return obj.valid_until and timezone.localdate() > obj.valid_until

    @admin.action(description="Mark expired (past valid_until)")
    def mark_expired(self, request, queryset):
        today = timezone.localdate()
        updated = 0
        for quote in queryset.filter(status__in=("draft", "sent")):
            if quote.valid_until and quote.valid_until < today:
                quote.status = "expired"
                quote.save(update_fields=["status", "updated_at"])
                updated += 1
        self.message_user(request, f"{updated} quote(s) marked expired.")

    @admin.action(description="Mark as sent")
    def mark_sent(self, request, queryset):
        queryset.filter(status="draft").update(status="sent")


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "total", "status", "payment_status", "shipping_method", "payment_ref", "payment_authority", "created_at")
    list_filter = ("status", "payment_status", "shipping_method")
    search_fields = ("user__email", "custom_request__title")
    readonly_fields = ("created_at", "updated_at")

    @admin.display(description="payment ref")
    def payment_ref(self, obj):
        payment = obj.payments.order_by("-created_at").first()
        return payment.ref_id if payment else "-"

    @admin.display(description="authority")
    def payment_authority(self, obj):
        payment = obj.payments.order_by("-created_at").first()
        return payment.authority if payment else "-"

    actions = ["advance_status"]

    @admin.action(description="Move to next production status")
    def advance_status(self, request, queryset):
        for obj in queryset:
            current = STATUS_ORDER.index(obj.status) if obj.status in STATUS_ORDER else 0
            if obj.status != "cancelled" and current < STATUS_ORDER.index("delivered"):
                obj.status = STATUS_ORDER[current + 1]
                obj.save(update_fields=["status", "updated_at"])
