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

from .models import Order, OrderItem, Review, ReviewImage
from .serializers import OrderCreateSerializer, OrderSerializer, ReviewCreateSerializer, ReviewSerializer
from users.models import Address, PaymentMethod
from products.models import Cart, CartItem, SKU, Product, Currency
from products.utils import convert_currency, get_market_currency
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
    
    # Get target currency from request or user
    target_currency_code = validated_data.get('currency_code') or validated_data.get('currency')
    if not target_currency_code:
        # Fallback to user's currency
        if hasattr(user, 'get_currency_code'):
            target_currency_code = user.get_currency_code()
        else:
            # Infer from user location
            user_location = getattr(user, 'location', 'KG')
            if user_location == 'US':
                target_currency_code = 'USD'
            else:
                target_currency_code = 'KGS'
    
    # Normalize currency code (handle symbol like '$' or 'сом')
    if target_currency_code in ['$', 'USD']:
        target_currency_code = 'USD'
    elif target_currency_code in ['сом', 'KGS', 'KGS']:
        target_currency_code = 'KGS'
    
    # Get currency object for symbol
    try:
        target_currency = Currency.objects.get(code=target_currency_code, is_active=True)
        currency_symbol = target_currency.symbol
    except Currency.DoesNotExist:
        # Fallback
        currency_symbol = '$' if target_currency_code == 'USD' else 'сом'
    
    # Calculate subtotal from cart items (convert to target currency)
    subtotal = Decimal('0.00')
    for cart_item in cart_items:
        sku = cart_item.sku
        # Get SKU's currency
        sku_currency = sku.get_currency()
        sku_currency_code = sku_currency.code if sku_currency else 'KGS'
        
        # Convert price if needed
        if sku_currency_code != target_currency_code:
            converted_price = Decimal(str(convert_currency(float(sku.price), sku_currency_code, target_currency_code)))
        else:
            converted_price = sku.price
        
        item_subtotal = converted_price * cart_item.quantity
        subtotal += item_subtotal
    
    # Get shipping cost and convert to target currency
    # Default shipping cost is 150 KGS (frontend uses 150)
    default_shipping_kgs = Decimal('150.00')
    shipping_cost_kgs = validated_data.get('shipping_cost', default_shipping_kgs)
    
    # If shipping_cost was provided, assume it's in KGS (original currency)
    # We'll convert it to target currency
    
    # Convert shipping cost to target currency
    if target_currency_code != 'KGS':
        shipping_cost = Decimal(str(convert_currency(float(shipping_cost_kgs), 'KGS', target_currency_code)))
    else:
        shipping_cost = shipping_cost_kgs
    
    tax = validated_data.get('tax', Decimal('0.00'))
    total_amount = subtotal + shipping_cost + tax
    
    # Set currency for order
    currency = currency_symbol
    currency_code = target_currency_code
    
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
        requested_delivery_date=validated_data.get('requested_delivery_date'),
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
    
    # Create order items from cart items (with converted prices)
    for cart_item in cart_items:
        sku = cart_item.sku
        product = sku.product
        
        # Get SKU's currency
        sku_currency = sku.get_currency()
        sku_currency_code = sku_currency.code if sku_currency else 'KGS'
        
        # Convert price to target currency
        if sku_currency_code != target_currency_code:
            converted_price = Decimal(str(convert_currency(float(sku.price), sku_currency_code, target_currency_code)))
        else:
            converted_price = sku.price
        
        # Calculate subtotal in target currency
        item_subtotal = converted_price * cart_item.quantity
        
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
            price=converted_price,  # Store converted price
            quantity=cart_item.quantity,
            subtotal=item_subtotal,  # Store converted subtotal
            image_url=image_url,
        )
    
    # Clear cart if use_cart is True
    if validated_data.get('use_cart', True):
        cart.items.all().delete()
    
    # Serialize and return order
    order_serializer = OrderSerializer(order, context={'request': request})
    
    return Response(order_serializer.data, status=status.HTTP_201_CREATED)


@extend_schema(
    summary="Create a review for an order product",
    description="Create a review with optional images for a product from an order.",
    request={
        'multipart/form-data': {
            'type': 'object',
            'properties': {
                'order_id': {'type': 'integer'},
                'product_id': {'type': 'integer'},
                'rating': {'type': 'integer', 'minimum': 1, 'maximum': 5},
                'comment': {'type': 'string'},
                'title': {'type': 'string', 'required': False},
                'images': {'type': 'array', 'items': {'type': 'string', 'format': 'binary'}},
            },
            'required': ['order_id', 'product_id', 'rating', 'comment'],
        }
    },
    responses={
        201: ReviewSerializer,
        400: OpenApiResponse(description="Validation error"),
        404: OpenApiResponse(description="Order or product not found"),
    },
    tags=["orders"],
)
@api_view(['POST'])
@permission_classes([IsAuthenticated])
@transaction.atomic
def create_review(request):
    """
    Create a review for a product from an order.
    
    Accepts multipart/form-data with:
    - order_id: ID of the order
    - product_id: ID of the product being reviewed
    - rating: Rating from 1 to 5 (required)
    - comment: Review text (required)
    - title: Review title (optional)
    - images: One or more image files (optional)
    """
    # Handle multipart form data
    data = request.data.copy()
    
    # Extract images from request.FILES
    # Handle both single file and multiple files
    # Frontend can send multiple files with the same name "images" or "images[]"
    images = []
    if 'images' in request.FILES:
        images = request.FILES.getlist('images')
    elif 'images[]' in request.FILES:
        images = request.FILES.getlist('images[]')
    elif 'image' in request.FILES:
        # Fallback for single image field name
        images = [request.FILES['image']]
    
    # Validate image files if provided
    for image in images:
        if not image.content_type.startswith('image/'):
            return Response(
                {'error': f'Invalid file type: {image.name}. Only image files are allowed.'},
                status=status.HTTP_400_BAD_REQUEST
            )
    
    serializer = ReviewCreateSerializer(data=data, context={'request': request})
    
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    user = request.user
    validated_data = serializer.validated_data
    
    # Get order and product
    try:
        order = Order.objects.get(id=validated_data['order_id'], user=user)
        product = Product.objects.get(id=validated_data['product_id'])
    except Order.DoesNotExist:
        return Response(
            {'error': 'Order not found or doesn\'t belong to user'},
            status=status.HTTP_404_NOT_FOUND
        )
    except Product.DoesNotExist:
        return Response(
            {'error': 'Product not found'},
            status=status.HTTP_404_NOT_FOUND
        )
    
    # Check if review already exists for this user, product, and order
    existing_review = Review.objects.filter(
        user=user,
        product=product,
        order=order
    ).first()
    
    if existing_review:
        return Response(
            {'error': 'You have already reviewed this product for this order'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    # Create review
    review = Review.objects.create(
        user=user,
        product=product,
        order=order,
        rating=validated_data['rating'],
        comment=validated_data['comment'],
        title=validated_data.get('title', ''),
        is_verified_purchase=True,  # Always true if linked to an order
        is_approved=False,  # Requires admin approval
    )
    
    # Create review images if provided
    review_images = []
    for image_file in images:
        review_image = ReviewImage.objects.create(
            review=review,
            image=image_file
        )
        review_images.append(review_image)
    
    # Ensure all files are saved and closed
    for review_image in review_images:
        if review_image.image:
            # Access the URL to ensure the file is saved
            _ = review_image.image.url
    
    # Refresh review from database to ensure images are loaded
    review.refresh_from_db()
    
    # Serialize and return review
    review_serializer = ReviewSerializer(review, context={'request': request})
    
    # Get serialized data and ensure it's JSON-serializable
    response_data = review_serializer.data
    
    return Response(response_data, status=status.HTTP_201_CREATED)
