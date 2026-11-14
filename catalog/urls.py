from django.urls import path

from . import views

urlpatterns = [
    path("catalog/processes", views.ProcessListView.as_view(), name="processes"),
    path("catalog/materials", views.MaterialListView.as_view(), name="materials"),
    path("catalog/categories", views.CategoryListView.as_view(), name="categories"),
    path("showcase", views.ShowcaseListView.as_view(), name="showcase-list"),
    path("showcase/<slug:slug>", views.ShowcaseDetailView.as_view(), name="showcase-detail"),
    path("showcase/<slug:slug>/like", views.LikeToggleView.as_view(), name="showcase-like"),
    path("showcase/<slug:slug>/save", views.SaveToCollectionView.as_view(), name="showcase-save"),
    path("showcase/<slug:slug>/comments", views.CommentListCreateView.as_view(), name="showcase-comments"),
    path("showcase/<slug:slug>/makes", views.MakeListCreateView.as_view(), name="showcase-makes"),
    path("showcase/<slug:slug>/download", views.ShowcaseDownloadView.as_view(), name="showcase-download"),
    path("collections", views.CollectionListCreateView.as_view(), name="collections"),
    path("collections/<int:pk>", views.CollectionDetailView.as_view(), name="collection-detail"),
    path("products", views.ProductListView.as_view(), name="product-list"),
    path("products/<slug:slug>", views.ProductDetailView.as_view(), name="product-detail"),
]
