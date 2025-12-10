"""
URLs for Referral Fee app.
"""

from django.urls import path
from . import views

app_name = 'referral_fee'

urlpatterns = [
    path('', views.fee_list, name='fee-list'),
    path('create/', views.fee_create, name='fee-create'),
    path('<int:fee_id>/', views.fee_detail, name='fee-detail'),
    path('<int:fee_id>/update/', views.fee_update, name='fee-update'),
    path('calculate/', views.calculate_fee, name='calculate-fee'),
    path('product/<int:product_id>/', views.get_fee_for_product, name='get-fee-for-product'),
]

