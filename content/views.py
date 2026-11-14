from rest_framework import status
from rest_framework.exceptions import APIException
from rest_framework.generics import ListAPIView, RetrieveAPIView
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from config import messages as msgs

from .models import BlogPost, ContactMessage, SiteSetting
from .serializers import (
    BlogPostDetailSerializer,
    BlogPostListSerializer,
    ContactMessageSerializer,
    SiteSettingSerializer,
)
from catalog.pagination import BlogPagination


class SiteSettingView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        return Response(SiteSettingSerializer(SiteSetting.load()).data)


class BlogListView(ListAPIView):
    serializer_class = BlogPostListSerializer
    permission_classes = [AllowAny]
    pagination_class = BlogPagination
    queryset = BlogPost.objects.filter(is_published=True)


class BlogDetailView(RetrieveAPIView):
    serializer_class = BlogPostDetailSerializer
    permission_classes = [AllowAny]
    lookup_field = "slug"
    queryset = BlogPost.objects.filter(is_published=True)


class ContactCreateView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = ContactMessageSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        message = serializer.save()
        return Response(
            {"detail": "پیام شما ثبت شد. به‌زودی پاسخ می‌دهیم.", "id": message.id},
            status=status.HTTP_201_CREATED,
        )
