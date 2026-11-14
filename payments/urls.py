from django.urls import path

from . import views

urlpatterns = [
    path("orders/<int:pk>/pay", views.PayOrderView.as_view(), name="order-pay"),
    path("payments/zarinpal/callback", views.ZarinpalCallbackView.as_view(), name="zarinpal-callback"),
]
