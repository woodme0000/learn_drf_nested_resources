"""learn_drf_nested_resources URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/1.8/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  url(r'^$', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  url(r'^$', Home.as_view(), name='home')
Including another URLconf
    1. Add an import:  from blog import urls as blog_urls
    2. Add a URL to urlpatterns:  url(r'^blog/', include(blog_urls))
"""
from django.conf.urls import include, url
from django.contrib import admin

from rest_framework.routers import DefaultRouter
from rest_framework_nested.routers import NestedSimpleRouter

from blogposts.views import BlogpostViewSet, CommentViewSet, NestedCommentViewSet

from .views import UserViewSet

router = DefaultRouter()
router.register(r'users', UserViewSet)
router.register(r'blogposts', BlogpostViewSet)
router.register(r'comments', CommentViewSet)

blogposts_router = NestedSimpleRouter(router, r'blogposts', lookup='blogpost')
blogposts_router.register(r'comments', NestedCommentViewSet)

urlpatterns = [
    url(r'^admin/', include(admin.site.urls)),
    url(r'^api/', include(router.urls)),
    url(r'^api/', include(blogposts_router.urls)),
    url(r'^o/', include('oauth2_provider.urls', namespace='oauth2_provider')),
]
