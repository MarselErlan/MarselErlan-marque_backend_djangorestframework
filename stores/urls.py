"""
URLs for Stores app.
"""

from django.urls import re_path
from . import views

app_name = 'stores'

urlpatterns = [
    re_path(r'^stores/?$', views.store_list, name='store-list'),
    re_path(r'^stores/register/?$', views.store_register, name='store-register'),
    re_path(r'^stores/my-stores/?$', views.my_stores, name='my-stores'),
    re_path(r'^stores/(?P<store_slug>[\w-]+)/?$', views.store_detail, name='store-detail'),
    re_path(r'^stores/(?P<store_slug>[\w-]+)/update/?$', views.store_update, name='store-update'),
    re_path(r'^stores/(?P<store_slug>[\w-]+)/products/?$', views.store_products, name='store-products'),
    re_path(r'^stores/(?P<store_slug>[\w-]+)/follow/?$', views.toggle_follow_store, name='toggle-follow-store'),
    re_path(r'^stores/(?P<store_slug>[\w-]+)/statistics/?$', views.store_statistics, name='store-statistics'),
]

