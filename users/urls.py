"""
URL Configuration for Users App
Routes for authentication, profile, addresses, payment methods, and notifications
"""

from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    SendVerificationView, VerifyCodeView, LogoutView, ProfileView, SetPasswordView,
    AddressViewSet, PaymentMethodViewSet, NotificationViewSet,
    PhoneNumberViewSet, OrderViewSet,
)

# Create router for ViewSets (allow optional trailing slash)
router = DefaultRouter()
router.trailing_slash = '/?'
router.register(r'addresses', AddressViewSet, basename='address')
router.register(r'payment-methods', PaymentMethodViewSet, basename='payment-method')
router.register(r'phones', PhoneNumberViewSet, basename='phone-number')
router.register(r'notifications', NotificationViewSet, basename='notification')
router.register(r'orders', OrderViewSet, basename='order')

# URL patterns
urlpatterns = [
    # ===========================
    # AUTHENTICATION ENDPOINTS
    # ===========================
    # POST /api/v1/auth/send-verification
    path('auth/send-verification', SendVerificationView.as_view(), name='send-verification'),
    
    # POST /api/v1/auth/verify-code
    path('auth/verify-code', VerifyCodeView.as_view(), name='verify-code'),
    
    # POST /api/v1/auth/logout
    path('auth/logout', LogoutView.as_view(), name='logout'),
    
    # GET/PUT /api/v1/auth/profile
    path('auth/profile', ProfileView.as_view(), name='profile'),
    
    # POST /api/v1/auth/set-password
    path('auth/set-password', SetPasswordView.as_view(), name='set-password'),
    
    # ===========================
    # PROFILE ENDPOINTS (ViewSets)
    # ===========================
    # Include router URLs under /profile/
    path('profile/', include(router.urls)),
]

"""
Complete API Endpoints:

Authentication:
- POST   /api/v1/auth/send-verification     - Send SMS verification code
- POST   /api/v1/auth/verify-code           - Verify code and login
- POST   /api/v1/auth/logout                - Logout
- GET    /api/v1/auth/profile               - Get user profile
- PUT    /api/v1/auth/profile               - Update user profile

Addresses:
- GET    /api/v1/profile/addresses          - List all addresses
- POST   /api/v1/profile/addresses          - Create address
- GET    /api/v1/profile/addresses/{id}     - Get address detail
- PUT    /api/v1/profile/addresses/{id}     - Update address
- DELETE /api/v1/profile/addresses/{id}     - Delete address

Payment Methods:
- GET    /api/v1/profile/payment-methods    - List all payment methods
- POST   /api/v1/profile/payment-methods    - Create payment method
- GET    /api/v1/profile/payment-methods/{id} - Get payment method detail
- PUT    /api/v1/profile/payment-methods/{id} - Update payment method
- DELETE /api/v1/profile/payment-methods/{id} - Delete payment method

Notifications:
- GET    /api/v1/profile/notifications      - List notifications
- GET    /api/v1/profile/notifications/{id} - Get notification detail
- PUT    /api/v1/profile/notifications/{id}/read - Mark as read
- PUT    /api/v1/profile/notifications/read-all - Mark all as read
"""

