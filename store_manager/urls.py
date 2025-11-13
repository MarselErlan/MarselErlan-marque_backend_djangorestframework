"""
URLs for Store Manager App
"""

from django.urls import path, re_path
from . import views

app_name = 'store_manager'

urlpatterns = [
    # Dashboard stats
    re_path(r'^dashboard/stats/?$', views.dashboard_stats, name='dashboard-stats'),
    
    # Orders
    re_path(r'^orders/?$', views.orders_list, name='orders-list'),
    re_path(r'^orders/(?P<order_id>\d+)/?$', views.order_detail, name='order-detail'),
    re_path(r'^orders/(?P<order_id>\d+)/status/?$', views.update_order_status, name='update-order-status'),
    re_path(r'^orders/(?P<order_id>\d+)/cancel/?$', views.cancel_order, name='cancel-order'),
    re_path(r'^orders/(?P<order_id>\d+)/resume/?$', views.resume_order, name='resume-order'),
    
    # Revenue analytics
    re_path(r'^revenue/analytics/?$', views.revenue_analytics, name='revenue-analytics'),
]

