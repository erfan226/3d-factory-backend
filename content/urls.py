from django.urls import path

from . import views

urlpatterns = [
    path("site-setting", views.SiteSettingView.as_view(), name="site-setting"),
    path("blog", views.BlogListView.as_view(), name="blog-list"),
    path("blog/<slug:slug>", views.BlogDetailView.as_view(), name="blog-detail"),
    path("contact", views.ContactCreateView.as_view(), name="contact"),
]
