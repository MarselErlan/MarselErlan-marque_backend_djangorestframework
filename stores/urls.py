"""
URLs for Stores app.
"""

from django.urls import re_path, path
from . import views
from . import views_store_admin

app_name = 'stores'

urlpatterns = [
    # Store Admin endpoints (for store owners to manage their products) - MUST come before store slug routes
    re_path(r'^stores/admin/products/?$', views_store_admin.store_admin_product_list, name='store-admin-product-list'),
    re_path(r'^stores/admin/products/create/?$', views_store_admin.store_admin_product_create, name='store-admin-product-create'),
    re_path(r'^stores/admin/products/(?P<product_id>\d+)/?$', views_store_admin.store_admin_product_detail, name='store-admin-product-detail'),
    re_path(r'^stores/admin/products/(?P<product_id>\d+)/update/?$', views_store_admin.store_admin_product_update, name='store-admin-product-update'),
    re_path(r'^stores/admin/products/(?P<product_id>\d+)/delete/?$', views_store_admin.store_admin_product_delete, name='store-admin-product-delete'),
    re_path(r'^stores/admin/my-stores/?$', views_store_admin.store_admin_my_stores, name='store-admin-my-stores'),
    
    # Public store endpoints
    re_path(r'^stores/?$', views.store_list, name='store-list'),
    re_path(r'^stores/register/?$', views.store_register, name='store-register'),
    re_path(r'^stores/my-stores/?$', views.my_stores, name='my-stores'),
    re_path(r'^stores/(?P<store_slug>[\w-]+)/?$', views.store_detail, name='store-detail'),
    re_path(r'^stores/(?P<store_slug>[\w-]+)/update/?$', views.store_update, name='store-update'),
    re_path(r'^stores/(?P<store_slug>[\w-]+)/products/?$', views.store_products, name='store-products'),
    re_path(r'^stores/(?P<store_slug>[\w-]+)/follow/?$', views.toggle_follow_store, name='toggle-follow-store'),
    re_path(r'^stores/(?P<store_slug>[\w-]+)/statistics/?$', views.store_statistics, name='store-statistics'),
]

