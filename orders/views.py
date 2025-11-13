"""
Views for Orders App
"""

from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django.db import transaction
from django.utils import timezone
from decimal import Decimal

from .models import Order, OrderItem
from .serializers import OrderCreateSerializer, OrderSerializer
from users.models import Address, PaymentMethod
from products.models import Cart, CartItem, SKU
from drf_spectacular.utils import extend_schema, OpenApiResponse, inline_serializer
from drf_spectacular.types import OpenApiTypes


@extend_schema(
    summary="Create a new order",
    description="Create an order from cart items. If use_cart is True, items are taken from user's cart.",
    request=OrderCreateSerializer,
    responses={
        201: OrderSerializer,
        400: OpenApiResponse(description="Validation error or cart is empty"),
        404: OpenApiResponse(description="Address or payment method not found"),
    },
    tags=["orders"],
)
@api_view(['POST'])
@permission_classes([IsAuthenticated])
@transaction.atomic
def create_order(request):
    """
    Create a new order from cart items or provided items.
    
    If use_cart=True, items are taken from user's cart and cart is cleared after order creation.
    """
    serializer = OrderCreateSerializer(data=request.data, context={'request': request})
    
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    user = request.user
    validated_data = serializer.validated_data
    
    # Get shipping address
    shipping_address = None
    if validated_data.get('shipping_address_id'):
        try:
            shipping_address = Address.objects.get(
                id=validated_data['shipping_address_id'],
                user=user
            )
        except Address.DoesNotExist:
            return Response(
                {'error': 'Shipping address not found'},
                status=status.HTTP_404_NOT_FOUND
            )
    
    # Get payment method
    payment_method_used = None
    if validated_data.get('payment_method_used_id'):
        try:
            payment_method_used = PaymentMethod.objects.get(
                id=validated_data['payment_method_used_id'],
                user=user
            )
        except PaymentMethod.DoesNotExist:
            return Response(
                {'error': 'Payment method not found'},
                status=status.HTTP_404_NOT_FOUND
            )
    
    # Get cart items if use_cart is True
    cart_items = []
    if validated_data.get('use_cart', True):
        try:
            cart = Cart.objects.get(user=user)
            cart_items = list(cart.items.select_related('sku', 'sku__product').all())
            
            if not cart_items:
                return Response(
                    {'error': 'Cart is empty'},
                    status=status.HTTP_400_BAD_REQUEST
                )
        except Cart.DoesNotExist:
            return Response(
                {'error': 'Cart not found'},
                status=status.HTTP_400_BAD_REQUEST
            )
    
    # Calculate subtotal from cart items
    subtotal = Decimal('0.00')
    for cart_item in cart_items:
        subtotal += cart_item.subtotal
    
    # Get shipping cost and tax
    shipping_cost = validated_data.get('shipping_cost', Decimal('350.00'))
    tax = validated_data.get('tax', Decimal('0.00'))
    total_amount = subtotal + shipping_cost + tax
    
    # Get currency from user
    currency = user.get_currency() if hasattr(user, 'get_currency') else 'сом'
    currency_code = user.get_currency_code() if hasattr(user, 'get_currency_code') else 'KGS'
    
    # Create order
    order = Order.objects.create(
        user=user,
        shipping_address=shipping_address,
        payment_method_used=payment_method_used,
        customer_name=validated_data['customer_name'],
        customer_phone=validated_data['customer_phone'],
        customer_email=validated_data.get('customer_email', ''),
        delivery_address=validated_data['delivery_address'],
        delivery_city=validated_data.get('delivery_city', ''),
        delivery_state=validated_data.get('delivery_state', ''),
        delivery_postal_code=validated_data.get('delivery_postal_code', ''),
        delivery_notes=validated_data.get('delivery_notes', ''),
        payment_method=validated_data.get('payment_method', 'cash'),
        subtotal=subtotal,
        shipping_cost=shipping_cost,
        tax=tax,
        total_amount=total_amount,
        currency=currency,
        currency_code=currency_code,
        status='pending',
        payment_status='pending',
    )
    
    # Create order items from cart items
    for cart_item in cart_items:
        sku = cart_item.sku
        product = sku.product
        
        # Get product image (prefer variant image, then first product image, then product main image)
        image_url = None
        
        if sku.variant_image:
            image_url = request.build_absolute_uri(sku.variant_image.url) if request else sku.variant_image.url
        elif hasattr(product, 'images') and product.images.exists():
            first_image = product.images.first()
            if first_image and first_image.image:
                image_url = request.build_absolute_uri(first_image.image.url) if request else first_image.image.url
        elif product.image:
            image_url = request.build_absolute_uri(product.image.url) if request else product.image.url
        
        OrderItem.objects.create(
            order=order,
            sku=sku,
            product_name=product.name,
            product_brand=product.brand or '',
            size=sku.size,
            color=sku.color,
            price=sku.price,
            quantity=cart_item.quantity,
            subtotal=cart_item.subtotal,
            image_url=image_url,
        )
    
    # Clear cart if use_cart is True
    if validated_data.get('use_cart', True):
        cart.items.all().delete()
    
    # Serialize and return order
    order_serializer = OrderSerializer(order, context={'request': request})
    
    return Response(order_serializer.data, status=status.HTTP_201_CREATED)
