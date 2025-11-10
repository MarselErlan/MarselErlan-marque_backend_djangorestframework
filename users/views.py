"""
Views for Users App
Handles authentication, profile management, addresses, payment methods, and notifications
"""

from rest_framework import serializers, status, viewsets
from rest_framework.decorators import api_view, permission_classes, action
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.authtoken.models import Token
from drf_spectacular.utils import extend_schema, inline_serializer
from django.contrib.auth import get_user_model
from django.utils import timezone
from django.db.models import Q
from django.conf import settings
import logging
import os

# Twilio imports
try:
    from twilio.rest import Client
    from twilio.base.exceptions import TwilioException
    TWILIO_AVAILABLE = True
except ImportError:
    TWILIO_AVAILABLE = False
    TwilioException = Exception

from orders.models import Order
from .models import Address, PaymentMethod, Notification
from .serializers import (
    UserSerializer, UserUpdateSerializer,
    AddressSerializer, AddressCreateSerializer,
    PaymentMethodSerializer, PaymentMethodCreateSerializer,
    NotificationSerializer, OrderListSerializer, OrderDetailSerializer,
    SendVerificationSerializer, VerifyCodeSerializer
)

User = get_user_model()
logger = logging.getLogger(__name__)

# ===========================
# TWILIO CONFIGURATION
# ===========================

TWILIO_ACCOUNT_SID = os.getenv("TWILIO_ACCOUNT_SID")
TWILIO_AUTH_TOKEN = os.getenv("TWILIO_AUTH_TOKEN")
TWILIO_VERIFY_SERVICE_SID = os.getenv("TWILIO_VERIFY_SERVICE_SID")

# Initialize Twilio client
TWILIO_READY = False
twilio_client = None

if TWILIO_AVAILABLE and TWILIO_ACCOUNT_SID and TWILIO_AUTH_TOKEN and TWILIO_VERIFY_SERVICE_SID:
    try:
        twilio_client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)
        TWILIO_READY = True
        logger.info("✅ Twilio client initialized successfully")
    except Exception as e:
        logger.warning(f"❌ Twilio client initialization failed: {e}")
else:
    logger.warning("📱 Twilio credentials not configured. SMS verification disabled.")


# ===========================
# TWILIO HELPER FUNCTIONS
# ===========================

def send_sms_via_twilio_verify(phone: str) -> bool:
    """
    Send SMS verification code via Twilio Verify API
    
    Args:
        phone: Phone number to send to (with country code)
        
    Returns:
        True if SMS sent successfully, False otherwise
    """
    if not TWILIO_READY:
        logger.debug(f"📱 Twilio not configured - cannot send verification SMS to {phone}")
        return False
    
    try:
        # Send SMS using Twilio Verify API
        verification = twilio_client.verify.v2.services(
            TWILIO_VERIFY_SERVICE_SID
        ).verifications.create(
            to=phone,
            channel='sms'
        )
        logger.info(f"✅ Twilio Verify SMS sent to {phone} - SID: {verification.sid}")
        return True
    except TwilioException as e:
        logger.error(f"❌ Twilio Verify failed for {phone}: {e}")
        return False
    except Exception as e:
        logger.error(f"❌ Unexpected error sending SMS to {phone}: {e}")
        return False


def verify_code_via_twilio_verify(phone: str, code: str) -> bool:
    """
    Verify code via Twilio Verify API
    
    Args:
        phone: Phone number
        code: Verification code to check
        
    Returns:
        True if code is valid, False otherwise
    """
    if not TWILIO_READY:
        logger.debug(f"📱 Twilio not configured - skipping Twilio verification for {phone}")
        return False
    
    try:
        # Verify code using Twilio Verify API
        logger.info(f"🔍 Checking code for {phone} with Twilio Verify...")
        verification_check = twilio_client.verify.v2.services(
            TWILIO_VERIFY_SERVICE_SID
        ).verification_checks.create(
            to=phone,
            code=code
        )
        is_approved = verification_check.status == 'approved'
        if is_approved:
            logger.info(f"✅ Twilio Verify code APPROVED for {phone}")
        else:
            logger.warning(f"❌ Twilio Verify code REJECTED for {phone}: Status={verification_check.status}")
        return is_approved
    except TwilioException as e:
        logger.error(f"❌ Twilio Verify check FAILED for {phone}: {type(e).__name__}: {e}")
        return False
    except Exception as e:
        logger.error(f"❌ Unexpected error verifying code for {phone}: {type(e).__name__}: {e}")
        return False


# ===========================
# AUTHENTICATION VIEWS
# ===========================

class SendVerificationView(APIView):
    """
    POST /api/v1/auth/send-verification
    Send SMS verification code to phone number
    """
    permission_classes = [AllowAny]
    
    @extend_schema(
        summary="Send SMS verification code",
        tags=["auth"],
        request=SendVerificationSerializer,
        responses={
            200: inline_serializer(
                name="SendVerificationResponse",
                fields={
                    "success": serializers.BooleanField(),
                    "message": serializers.CharField(),
                    "phone": serializers.CharField(),
                    "market": serializers.CharField(),
                    "language": serializers.CharField(),
                    "expires_in_minutes": serializers.IntegerField(),
                },
            )
        },
    )
    def post(self, request):
        serializer = SendVerificationSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        phone = serializer.validated_data['phone']
        
        # Determine market based on country code
        market = 'KG' if phone.startswith('+996') else 'US'
        language = 'ru' if market == 'KG' else 'en'
        expiry_minutes = 10 if market == 'KG' else 15
        
        if not TWILIO_READY:
            if not settings.TESTING:
                logger.error("❌ Twilio credentials not configured. Cannot send verification SMS.")
            return Response({
                'success': False,
                'detail': 'SMS verification is temporarily unavailable. Please contact support.'
            }, status=status.HTTP_503_SERVICE_UNAVAILABLE)
        
        # Try to send SMS via Twilio Verify
        sms_sent = send_sms_via_twilio_verify(phone)
        
        if not sms_sent:
            if not settings.TESTING:
                logger.error(f"❌ Failed to send verification SMS to {phone} via Twilio Verify.")
            return Response({
                'success': False,
                'detail': 'Failed to send verification code. Please try again later.'
            }, status=status.HTTP_502_BAD_GATEWAY)
        
        # Twilio Verify sent successfully
        # Note: Twilio generates and stores the code, we don't need to
        logger.info(f"✅ SMS sent to {phone} via Twilio Verify")
        
        return Response({
            'success': True,
            'message': f'Verification code sent to {phone}',
            'phone': phone,
            'market': market,
            'language': language,
            'expires_in_minutes': expiry_minutes
        }, status=status.HTTP_200_OK)


class VerifyCodeView(APIView):
    """
    POST /api/v1/auth/verify-code
    Verify SMS code and authenticate user
    """
    permission_classes = [AllowAny]
    
    @extend_schema(
        summary="Verify SMS code and obtain token",
        tags=["auth"],
        request=VerifyCodeSerializer,
        responses={
            200: inline_serializer(
                name="VerifyCodeResponse",
                fields={
                    "access_token": serializers.CharField(),
                    "token_type": serializers.CharField(),
                    "expires_in": serializers.IntegerField(),
                    "user": inline_serializer(
                        name="VerifyCodeUserPayload",
                        fields={
                            "id": serializers.CharField(),
                            "name": serializers.CharField(),
                            "phone": serializers.CharField(),
                            "full_name": serializers.CharField(allow_null=True),
                            "is_active": serializers.BooleanField(),
                            "is_verified": serializers.BooleanField(),
                        },
                    ),
                    "market": serializers.CharField(),
                    "is_new_user": serializers.BooleanField(),
                },
            )
        },
    )
    def post(self, request):
        serializer = VerifyCodeSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        phone = serializer.validated_data['phone']
        code = serializer.validated_data['verification_code']
        
        # Determine market based on phone
        market = 'KG' if phone.startswith('+996') else 'US'
        language = 'ru' if market == 'KG' else 'en'
        
        if not TWILIO_READY:
            return Response({
                'detail': 'SMS verification is temporarily unavailable. Please contact support.'
            }, status=status.HTTP_503_SERVICE_UNAVAILABLE)
        
        # Using Twilio Verify - codes are checked by Twilio
        code_valid = verify_code_via_twilio_verify(phone, code)
        if not code_valid:
            return Response({
                'detail': 'Invalid or expired verification code'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Code is valid - get or create user
        user, created = User.objects.get_or_create(
            phone=phone,
            defaults={
                'full_name': phone.split('+')[-1][:10],  # Use last 10 digits as temp name
                'market': market,
                'language': language,
                'is_verified': True,
                'is_active': True,
            }
        )
        
        # If user exists, update last login and verification status
        if not created:
            user.is_verified = True
            user.is_active = True
            user.market = market  # Update market based on phone
            user.last_login = timezone.now()
            user.save()
            logger.info(f"🔄 Existing user logged in: {user.id} - {phone}")
        else:
            logger.info(f"✅ New user created: {user.id} - {phone} - Market: {market}")
        
        # Create or get auth token
        token, _ = Token.objects.get_or_create(user=user)
        
        return Response({
            'access_token': token.key,
            'token_type': 'bearer',
            'expires_in': 43200 * 60,  # 30 days in seconds
            'user': {
                'id': str(user.id),
                'name': user.name or user.get_full_name() or 'User',
                'phone': user.phone,
                'full_name': user.get_full_name(),
                'is_active': user.is_active,
                'is_verified': user.is_verified,
            },
            'market': user.market,
            'is_new_user': created
        }, status=status.HTTP_200_OK)


class LogoutView(APIView):
    """
    POST /api/v1/auth/logout
    Logout user and delete auth token
    """
    permission_classes = [IsAuthenticated]
    
    @extend_schema(
        summary="Logout the current user",
        tags=["auth"],
        request=None,
        responses={
            200: inline_serializer(
                name="LogoutResponse",
                fields={
                    "success": serializers.BooleanField(),
                    "message": serializers.CharField(),
                },
            )
        },
    )
    def post(self, request):
        try:
            # Delete the user's token
            request.user.auth_token.delete()
            return Response({
                'success': True,
                'message': 'Successfully logged out'
            }, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({
                'success': False,
                'message': 'Error logging out'
            }, status=status.HTTP_400_BAD_REQUEST)


class ProfileView(APIView):
    """
    GET /api/v1/auth/profile - Get user profile
    PUT /api/v1/auth/profile - Update user profile
    """
    permission_classes = [IsAuthenticated]
    
    @extend_schema(
        summary="Retrieve current user profile",
        tags=["auth"],
        responses={200: UserSerializer},
    )
    def get(self, request):
        """Get user profile"""
        serializer = UserSerializer(request.user)
        return Response(serializer.data, status=status.HTTP_200_OK)
    
    @extend_schema(
        summary="Update current user profile",
        tags=["auth"],
        request=UserUpdateSerializer,
        responses={200: UserSerializer},
    )
    def put(self, request):
        """Update user profile"""
        serializer = UserUpdateSerializer(request.user, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response({
                'success': True,
                'message': 'Profile updated successfully',
                'user': UserSerializer(request.user).data
            }, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


# ===========================
# ADDRESS VIEWS
# ===========================

class AddressViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing user addresses
    GET /api/v1/profile/addresses - List addresses
    POST /api/v1/profile/addresses - Create address
    PUT /api/v1/profile/addresses/{id} - Update address
    DELETE /api/v1/profile/addresses/{id} - Delete address
    """
    permission_classes = [IsAuthenticated]
    serializer_class = AddressSerializer
    
    def get_queryset(self):
        """Return addresses for current user only"""
        return Address.objects.filter(user=self.request.user).order_by('-is_default', '-created_at')
    
    def get_serializer_class(self):
        """Use different serializer for create"""
        if self.action == 'create':
            return AddressCreateSerializer
        return AddressSerializer
    
    def list(self, request, *args, **kwargs):
        """List all addresses for user"""
        queryset = self.get_queryset()
        serializer = self.get_serializer(queryset, many=True)
        return Response({
            'success': True,
            'addresses': serializer.data,
            'total': queryset.count()
        }, status=status.HTTP_200_OK)
    
    def create(self, request, *args, **kwargs):
        """Create new address"""
        serializer = self.get_serializer(data=request.data)
        if serializer.is_valid():
            # Create address with user and market
            address = serializer.save(
                user=request.user,
                market=request.user.market
            )
            
            # If set as default, unset other defaults
            if address.is_default:
                Address.objects.filter(
                    user=request.user,
                    is_default=True
                ).exclude(id=address.id).update(is_default=False)
            
            return Response({
                'success': True,
                'message': 'Address created successfully',
                'address': AddressSerializer(address).data
            }, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    def update(self, request, *args, **kwargs):
        """Update address"""
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        serializer = AddressCreateSerializer(
            instance,
            data=request.data,
            partial=partial,
            context=self.get_serializer_context()
        )
        
        if serializer.is_valid():
            address = serializer.save()
            
            # If set as default, unset other defaults
            if address.is_default:
                Address.objects.filter(
                    user=request.user,
                    is_default=True
                ).exclude(id=address.id).update(is_default=False)
            
            return Response({
                'success': True,
                'message': 'Address updated successfully',
                'address': AddressSerializer(address).data
            }, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


    
    def destroy(self, request, *args, **kwargs):
        """Delete address"""
        instance = self.get_object()
        instance.delete()
        return Response({
            'success': True,
            'message': 'Address deleted successfully'
        }, status=status.HTTP_200_OK)


# ===========================
# PAYMENT METHOD VIEWS
# ===========================

class PaymentMethodViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing payment methods
    GET /api/v1/profile/payment-methods - List payment methods
    POST /api/v1/profile/payment-methods - Create payment method
    PUT /api/v1/profile/payment-methods/{id} - Update payment method
    DELETE /api/v1/profile/payment-methods/{id} - Delete payment method
    """
    permission_classes = [IsAuthenticated]
    serializer_class = PaymentMethodSerializer
    
    def get_queryset(self):
        """Return payment methods for current user only"""
        return PaymentMethod.objects.filter(user=self.request.user).order_by('-is_default', '-created_at')
    
    def get_serializer_class(self):
        """Use different serializer for create"""
        if self.action == 'create':
            return PaymentMethodCreateSerializer
        return PaymentMethodSerializer
    
    def list(self, request, *args, **kwargs):
        """List all payment methods for user"""
        queryset = self.get_queryset()
        serializer = self.get_serializer(queryset, many=True)
        return Response({
            'success': True,
            'payment_methods': serializer.data,
            'total': queryset.count()
        }, status=status.HTTP_200_OK)
    
    def create(self, request, *args, **kwargs):
        """Create new payment method"""
        serializer = self.get_serializer(data=request.data)
        if serializer.is_valid():
            # Extract card number and mask it
            card_number = serializer.validated_data.pop('card_number')
            
            # Create payment method with masked card number
            payment_method = PaymentMethod.objects.create(
                user=request.user,
                market=request.user.market,
                card_number_masked=f"****{card_number[-4:]}",
                **serializer.validated_data
            )
            
            # If set as default, unset other defaults
            if payment_method.is_default:
                PaymentMethod.objects.filter(
                    user=request.user,
                    is_default=True
                ).exclude(id=payment_method.id).update(is_default=False)
            
            return Response({
                'success': True,
                'message': 'Payment method added successfully',
                'payment_method': PaymentMethodSerializer(payment_method).data
            }, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    def update(self, request, *args, **kwargs):
        """Update payment method (only is_default can be updated)"""
        instance = self.get_object()
        
        # Only allow updating is_default
        if 'is_default' in request.data:
            instance.is_default = request.data['is_default']
            
            # If set as default, unset other defaults
            if instance.is_default:
                PaymentMethod.objects.filter(
                    user=request.user,
                    is_default=True
                ).exclude(id=instance.id).update(is_default=False)
            
            instance.save()
            
            return Response({
                'success': True,
                'message': 'Payment method updated successfully'
            }, status=status.HTTP_200_OK)
        
        return Response({
            'success': False,
            'message': 'Only is_default field can be updated'
        }, status=status.HTTP_400_BAD_REQUEST)
    
    def destroy(self, request, *args, **kwargs):
        """Delete payment method"""
        instance = self.get_object()
        instance.delete()
        return Response({
            'success': True,
            'message': 'Payment method deleted successfully'
        }, status=status.HTTP_200_OK)


# ===========================
# ORDER VIEWS
# ===========================

class OrderViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet for managing user orders
    GET /api/v1/profile/orders - List orders
    GET /api/v1/profile/orders/{id} - Order detail
    POST /api/v1/profile/orders/{id}/cancel - Cancel order (custom action)
    """
    permission_classes = [IsAuthenticated]
    serializer_class = OrderListSerializer

    def get_queryset(self):
        """Return orders for the current user with optional status filter"""
        queryset = (
            Order.objects
            .filter(user=self.request.user)
            .select_related('shipping_address', 'payment_method_used')
            .prefetch_related('items')
            .order_by('-order_date')
        )

        status_filter = self.request.query_params.get('status')
        if status_filter:
            queryset = queryset.filter(status=status_filter)

        return queryset

    def get_serializer_class(self):
        if self.action == 'retrieve':
            return OrderDetailSerializer
        return OrderListSerializer

    def list(self, request, *args, **kwargs):
        queryset = self.get_queryset()
        limit = int(request.query_params.get('limit', 20))
        offset = int(request.query_params.get('offset', 0))

        total = queryset.count()
        orders = queryset[offset:offset + limit]
        serializer = self.get_serializer(orders, many=True)
        has_more = (offset + limit) < total

        return Response({
            'success': True,
            'orders': serializer.data,
            'total': total,
            'has_more': has_more
        }, status=status.HTTP_200_OK)

    def retrieve(self, request, *args, **kwargs):
        order = self.get_object()
        serializer = self.get_serializer(order)
        return Response({
            'success': True,
            'order': serializer.data
        }, status=status.HTTP_200_OK)

    @action(detail=True, methods=['post'], url_path='cancel')
    def cancel_order(self, request, pk=None):
        """Allow user to cancel an order if still pending/confirmed"""
        order = self.get_object()

        if not order.can_cancel:
            return Response({
                'success': False,
                'message': 'Order cannot be cancelled at this stage.'
            }, status=status.HTTP_400_BAD_REQUEST)

        order.status = 'cancelled'
        order.cancelled_date = timezone.now()
        order.save(update_fields=['status', 'cancelled_date', 'updated_at'])

        return Response({
            'success': True,
            'message': 'Order cancelled successfully.',
            'order_id': order.id,
            'status': order.status
        }, status=status.HTTP_200_OK)


# ===========================
# NOTIFICATION VIEWS
# ===========================

class NotificationViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet for user notifications (read-only + custom actions)
    GET /api/v1/profile/notifications - List notifications
    PUT /api/v1/profile/notifications/{id}/read - Mark as read
    PUT /api/v1/profile/notifications/read-all - Mark all as read
    """
    permission_classes = [IsAuthenticated]
    serializer_class = NotificationSerializer
    
    def get_queryset(self):
        """Return notifications for current user only"""
        queryset = Notification.objects.filter(user=self.request.user)
        
        # Filter by unread only if requested
        if self.request.query_params.get('unread_only') == 'true':
            queryset = queryset.filter(is_read=False)
        
        return queryset.order_by('-created_at')
    
    def list(self, request, *args, **kwargs):
        """List notifications with pagination"""
        queryset = self.get_queryset()
        
        # Pagination
        limit = int(request.query_params.get('limit', 20))
        offset = int(request.query_params.get('offset', 0))
        
        total = queryset.count()
        unread_count = queryset.filter(is_read=False).count()
        
        notifications = queryset[offset:offset + limit]
        serializer = self.get_serializer(notifications, many=True)
        
        return Response({
            'success': True,
            'notifications': serializer.data,
            'total': total,
            'unread_count': unread_count
        }, status=status.HTTP_200_OK)
    
    @action(detail=True, methods=['put'], url_path='read')
    def mark_read(self, request, pk=None):
        """Mark notification as read"""
        notification = self.get_object()
        notification.is_read = True
        notification.save()
        
        return Response({
            'success': True,
            'message': 'Notification marked as read'
        }, status=status.HTTP_200_OK)
    
    @action(detail=False, methods=['put'], url_path='read-all')
    def mark_all_read(self, request):
        """Mark all notifications as read"""
        count = Notification.objects.filter(
            user=request.user,
            is_read=False
        ).update(is_read=True)
        
        return Response({
            'success': True,
            'message': 'All notifications marked as read',
            'count': count
        }, status=status.HTTP_200_OK)
