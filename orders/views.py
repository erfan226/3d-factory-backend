from django.db import IntegrityError, transaction
from rest_framework import status
from rest_framework.exceptions import APIException
from rest_framework.generics import ListAPIView, RetrieveAPIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from config import messages as msgs
from config.exceptions import NotFound

from .models import CustomRequest, Order, Quote, RequestMessage
from .serializers import (
    CustomRequestCreateSerializer,
    CustomRequestDetailSerializer,
    CustomRequestListSerializer,
    OrderSerializer,
    QuoteSerializer,
    RequestMessageSerializer,
)


class ConflictException(APIException):
    status_code = 409


def _conflict(code, persian):
    return ConflictException({"detail": persian, "code": code})


class CustomRequestListCreateView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        qs = CustomRequest.objects.filter(user=request.user).select_related("process", "material")
        status_filter = request.query_params.get("status")
        if status_filter:
            qs = qs.filter(status=status_filter)
        serializer = CustomRequestListSerializer(qs, many=True)
        return Response(serializer.data)

    def post(self, request):
        serializer = CustomRequestCreateSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        custom_request = serializer.save()
        return Response(
            CustomRequestDetailSerializer(custom_request).data, status=status.HTTP_201_CREATED
        )


class CustomRequestDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def get_object(self, request, pk):
        # Another user's request must look like a missing object.
        try:
            return CustomRequest.objects.get(pk=pk, user=request.user)
        except CustomRequest.DoesNotExist:
            raise NotFound()

    def get(self, request, pk):
        custom_request = self.get_object(request, pk)
        data = CustomRequestDetailSerializer(custom_request).data
        latest_quote = custom_request.quotes.order_by("-created_at").first()
        data["quote"] = (
            {
                "id": latest_quote.id,
                "price": latest_quote.price,
                "lead_time_days": latest_quote.lead_time_days,
                "message": latest_quote.message,
                "valid_until": latest_quote.valid_until,
                "status": latest_quote.status,
                "is_expired": latest_quote.is_expired,
            }
            if latest_quote
            else None
        )
        return Response(data)


class RequestMessageCreateView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        try:
            custom_request = CustomRequest.objects.get(pk=pk, user=request.user)
        except CustomRequest.DoesNotExist:
            raise NotFound()
        body = (request.data.get("body") or "").strip()
        if not body:
            return Response(
                {"detail": "متن پیام نمی‌تواند خالی باشد.", "code": msgs.VALIDATION_ERROR},
                status=status.HTTP_400_BAD_REQUEST,
            )
        message = RequestMessage.objects.create(
            request=custom_request, author=request.user, body=body
        )
        return Response(RequestMessageSerializer(message).data, status=status.HTTP_201_CREATED)


class AcceptQuoteView(APIView):
    """Accept the latest sent quote; creates exactly one order per quote."""

    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        try:
            custom_request = CustomRequest.objects.get(pk=pk, user=request.user)
        except CustomRequest.DoesNotExist:
            raise NotFound()

        try:
            with transaction.atomic():
                locked = CustomRequest.objects.select_for_update().get(pk=custom_request.pk)
                quote = locked.quotes.order_by("-created_at").first()
                if not quote or quote.status != "sent":
                    raise _conflict(msgs.QUOTE_NOT_SENT, "پیش‌فاکتوری برای تایید وجود ندارد.")
                if quote.is_expired:
                    raise _conflict(msgs.QUOTE_EXPIRED, msgs.PERSIAN_ERRORS[msgs.QUOTE_EXPIRED])
                order = Order.objects.create(
                    user=request.user,
                    custom_request=locked,
                    quote=quote,
                    total=quote.price,
                    status="quoted",
                )
                quote.status = "accepted"
                locked.status = "quoted"
                quote.save(update_fields=["status", "updated_at"])
                locked.save(update_fields=["status", "updated_at"])
        except ConflictException:
            raise
        except IntegrityError:
            # Unique constraint on quote: a second accept hits this path.
            raise _conflict(msgs.QUOTE_ALREADY_USED, msgs.PERSIAN_ERRORS[msgs.QUOTE_ALREADY_USED])

        return Response(
            {"detail": "سفارش شما با موفقیت ثبت شد.", "order_id": order.id, "order": OrderSerializer(order).data},
            status=status.HTTP_200_OK,
        )


class RejectQuoteView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        try:
            custom_request = CustomRequest.objects.get(pk=pk, user=request.user)
        except CustomRequest.DoesNotExist:
            raise NotFound()
        quote = custom_request.quotes.order_by("-created_at").first()
        if not quote or quote.status not in ("sent", "draft"):
            raise _conflict(msgs.QUOTE_NOT_SENT, "این پیش‌فاکتور قابل رد کردن نیست.")
        quote.status = "rejected"
        quote.save(update_fields=["status", "updated_at"])
        return Response({"detail": "پیش‌فاکتور رد شد.", "quote": QuoteSerializer(quote).data})


class OrderListView(ListAPIView):
    serializer_class = OrderSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = None

    def get_queryset(self):
        return Order.objects.filter(user=self.request.user).select_related("quote", "custom_request", "product")


class OrderDetailView(RetrieveAPIView):
    serializer_class = OrderSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Order.objects.filter(user=self.request.user).select_related("quote", "custom_request", "product")
