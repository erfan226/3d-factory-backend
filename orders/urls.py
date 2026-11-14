from django.urls import path

from . import views

urlpatterns = [
    path("custom-requests", views.CustomRequestListCreateView.as_view(), name="custom-requests"),
    path("custom-requests/<int:pk>", views.CustomRequestDetailView.as_view(), name="custom-request-detail"),
    path("custom-requests/<int:pk>/messages", views.RequestMessageCreateView.as_view(), name="request-messages"),
    path("custom-requests/<int:pk>/accept-quote", views.AcceptQuoteView.as_view(), name="accept-quote"),
    path("custom-requests/<int:pk>/reject-quote", views.RejectQuoteView.as_view(), name="reject-quote"),
    path("orders", views.OrderListView.as_view(), name="orders"),
    path("orders/<int:pk>", views.OrderDetailView.as_view(), name="order-detail"),
]
