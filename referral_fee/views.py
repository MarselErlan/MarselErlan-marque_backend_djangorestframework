"""
Views for Referral Fee app.
"""

from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated, IsAdminUser
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from decimal import Decimal

from .models import ReferralFee
from .serializers import (
    ReferralFeeSerializer,
    ReferralFeeListSerializer,
    CalculateFeeSerializer,
)
from products.models import Product
from drf_spectacular.utils import extend_schema, OpenApiResponse, OpenApiParameter
from drf_spectacular.types import OpenApiTypes


@extend_schema(
    summary="List all referral fees",
    description="Get a list of all referral fee configurations",
    responses={
        200: ReferralFeeListSerializer(many=True),
        401: OpenApiResponse(description="Authentication required"),
    },
    tags=["referral-fee"],
)
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def fee_list(request):
    """
    List all referral fees.
    Only active fees are shown by default, use ?include_inactive=true to see all.
    """
    include_inactive = request.query_params.get('include_inactive', 'false').lower() == 'true'
    
    queryset = ReferralFee.objects.select_related(
        'category',
        'subcategory',
        'second_subcategory'
    ).all()
    
    if not include_inactive:
        queryset = queryset.filter(is_active=True)
    
    serializer = ReferralFeeListSerializer(queryset, many=True)
    return Response({
        'success': True,
        'fees': serializer.data,
        'total': queryset.count(),
    }, status=status.HTTP_200_OK)


@extend_schema(
    summary="Get referral fee detail",
    description="Get detailed information about a specific referral fee",
    responses={
        200: ReferralFeeSerializer,
        404: OpenApiResponse(description="Fee not found"),
    },
    tags=["referral-fee"],
)
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def fee_detail(request, fee_id):
    """Get detailed information about a specific referral fee."""
    fee = get_object_or_404(ReferralFee, id=fee_id)
    serializer = ReferralFeeSerializer(fee)
    return Response({
        'success': True,
        'fee': serializer.data,
    }, status=status.HTTP_200_OK)


@extend_schema(
    summary="Create referral fee",
    description="Create a new referral fee configuration (admin only)",
    request=ReferralFeeSerializer,
    responses={
        201: ReferralFeeSerializer,
        400: OpenApiResponse(description="Validation error"),
        403: OpenApiResponse(description="Admin access required"),
    },
    tags=["referral-fee"],
)
@api_view(['POST'])
@permission_classes([IsAdminUser])
def fee_create(request):
    """Create a new referral fee configuration."""
    serializer = ReferralFeeSerializer(data=request.data)
    if serializer.is_valid():
        fee = serializer.save()
        return Response({
            'success': True,
            'fee': ReferralFeeSerializer(fee).data,
        }, status=status.HTTP_201_CREATED)
    return Response({
        'success': False,
        'errors': serializer.errors,
    }, status=status.HTTP_400_BAD_REQUEST)


@extend_schema(
    summary="Update referral fee",
    description="Update an existing referral fee configuration (admin only)",
    request=ReferralFeeSerializer,
    responses={
        200: ReferralFeeSerializer,
        400: OpenApiResponse(description="Validation error"),
        403: OpenApiResponse(description="Admin access required"),
        404: OpenApiResponse(description="Fee not found"),
    },
    tags=["referral-fee"],
)
@api_view(['PUT', 'PATCH'])
@permission_classes([IsAdminUser])
def fee_update(request, fee_id):
    """Update an existing referral fee configuration."""
    fee = get_object_or_404(ReferralFee, id=fee_id)
    serializer = ReferralFeeSerializer(fee, data=request.data, partial=True)
    if serializer.is_valid():
        updated_fee = serializer.save()
        return Response({
            'success': True,
            'fee': ReferralFeeSerializer(updated_fee).data,
        }, status=status.HTTP_200_OK)
    return Response({
        'success': False,
        'errors': serializer.errors,
    }, status=status.HTTP_400_BAD_REQUEST)


@extend_schema(
    summary="Calculate fee for product",
    description="Calculate the referral fee for a product based on order amount",
    request=CalculateFeeSerializer,
    responses={
        200: OpenApiResponse(description="Fee calculation result"),
        400: OpenApiResponse(description="Validation error"),
        404: OpenApiResponse(description="Product not found"),
    },
    tags=["referral-fee"],
)
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def calculate_fee(request):
    """
    Calculate referral fee for a product based on order amount.
    
    Returns:
    - fee: ReferralFee object details
    - fee_amount: Calculated fee amount
    - order_amount: Original order amount
    """
    serializer = CalculateFeeSerializer(data=request.data)
    if not serializer.is_valid():
        return Response({
            'success': False,
            'errors': serializer.errors,
        }, status=status.HTTP_400_BAD_REQUEST)
    
    product_id = serializer.validated_data['product_id']
    order_amount = serializer.validated_data['order_amount']
    
    try:
        product = Product.objects.select_related(
            'category',
            'subcategory',
            'second_subcategory'
        ).get(id=product_id)
    except Product.DoesNotExist:
        return Response({
            'success': False,
            'error': 'Product not found',
        }, status=status.HTTP_404_NOT_FOUND)
    
    # Get the most specific fee for this product
    fee = ReferralFee.get_fee_for_product(product)
    
    if not fee:
        return Response({
            'success': True,
            'fee': None,
            'fee_amount': Decimal('0.00'),
            'order_amount': order_amount,
            'message': 'No fee configuration found for this product',
        }, status=status.HTTP_200_OK)
    
    # Calculate fee amount
    fee_amount = fee.calculate_fee(order_amount)
    
    return Response({
        'success': True,
        'fee': ReferralFeeSerializer(fee).data,
        'fee_amount': str(fee_amount),
        'order_amount': str(order_amount),
        'fee_percentage': str(fee.fee_percentage),
        'fee_fixed': str(fee.fee_fixed),
    }, status=status.HTTP_200_OK)


@extend_schema(
    summary="Get fee for product",
    description="Get the referral fee configuration for a specific product",
    responses={
        200: ReferralFeeSerializer,
        404: OpenApiResponse(description="Product or fee not found"),
    },
    tags=["referral-fee"],
)
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_fee_for_product(request, product_id):
    """
    Get the referral fee configuration for a specific product.
    
    Returns the most specific fee that matches the product's category structure.
    """
    try:
        product = Product.objects.select_related(
            'category',
            'subcategory',
            'second_subcategory'
        ).get(id=product_id)
    except Product.DoesNotExist:
        return Response({
            'success': False,
            'error': 'Product not found',
        }, status=status.HTTP_404_NOT_FOUND)
    
    fee = ReferralFee.get_fee_for_product(product)
    
    if not fee:
        return Response({
            'success': True,
            'fee': None,
            'message': 'No fee configuration found for this product',
        }, status=status.HTTP_200_OK)
    
    serializer = ReferralFeeSerializer(fee)
    return Response({
        'success': True,
        'fee': serializer.data,
    }, status=status.HTTP_200_OK)
