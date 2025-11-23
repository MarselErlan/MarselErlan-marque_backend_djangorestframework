"""
Currency conversion API views.
"""

from rest_framework import status, serializers
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView
from drf_spectacular.utils import (
    OpenApiParameter,
    OpenApiTypes,
    OpenApiResponse,
    extend_schema,
    inline_serializer,
)

from .models import Currency
from .serializers import CurrencySerializer
from .utils import convert_currency, get_market_currency
from rest_framework.permissions import IsAuthenticated, IsAdminUser
from django.core.management import call_command
from io import StringIO
from io import StringIO


class CurrencyListView(APIView):
    """List all active currencies."""
    
    permission_classes = [AllowAny]
    
    @extend_schema(
        summary="List all currencies",
        description="Get a list of all active currencies with their exchange rates",
        responses={
            200: CurrencySerializer(many=True),
        },
    )
    def get(self, request):
        currencies = Currency.objects.filter(is_active=True).order_by('code')
        serializer = CurrencySerializer(currencies, many=True)
        return Response(serializer.data)


class CurrencyConvertView(APIView):
    """Convert amount from one currency to another."""
    
    permission_classes = [AllowAny]
    
    @extend_schema(
        summary="Convert currency",
        description="Convert an amount from one currency to another",
        parameters=[
            OpenApiParameter(
                name="amount",
                type=OpenApiTypes.FLOAT,
                location=OpenApiParameter.QUERY,
                required=True,
                description="Amount to convert",
            ),
            OpenApiParameter(
                name="from",
                type=OpenApiTypes.STR,
                location=OpenApiParameter.QUERY,
                required=True,
                description="Source currency code (e.g., USD, KGS)",
            ),
            OpenApiParameter(
                name="to",
                type=OpenApiTypes.STR,
                location=OpenApiParameter.QUERY,
                required=True,
                description="Target currency code (e.g., USD, KGS)",
            ),
        ],
        responses={
            200: inline_serializer(
                name="CurrencyConvertResponse",
                fields={
                    "amount": serializers.FloatField(),
                    "from_currency": serializers.CharField(),
                    "to_currency": serializers.CharField(),
                    "converted_amount": serializers.FloatField(),
                    "exchange_rate": serializers.FloatField(),
                },
            ),
            400: inline_serializer(
                name="ErrorResponse",
                fields={"error": serializers.CharField()},
            ),
        },
    )
    def get(self, request):
        amount = request.query_params.get('amount')
        from_currency = request.query_params.get('from')
        to_currency = request.query_params.get('to')
        
        if not amount or not from_currency or not to_currency:
            return Response(
                {"error": "Missing required parameters: amount, from, to"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            amount_float = float(amount)
        except ValueError:
            return Response(
                {"error": "Invalid amount. Must be a number."},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Get currency info
        try:
            from_curr = Currency.objects.get(code=from_currency.upper(), is_active=True)
            to_curr = Currency.objects.get(code=to_currency.upper(), is_active=True)
        except Currency.DoesNotExist:
            return Response(
                {"error": "Currency not found. Please check currency codes."},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Calculate exchange rate
        if from_curr.is_base:
            exchange_rate = float(to_curr.exchange_rate)
        elif to_curr.is_base:
            exchange_rate = 1.0 / float(from_curr.exchange_rate)
        else:
            # Both are not base, convert through base
            exchange_rate = float(to_curr.exchange_rate) / float(from_curr.exchange_rate)
        
        converted_amount = convert_currency(amount_float, from_currency.upper(), to_currency.upper())
        
        return Response({
            "amount": amount_float,
            "from_currency": from_currency.upper(),
            "to_currency": to_currency.upper(),
            "converted_amount": round(converted_amount, 2),
            "exchange_rate": round(exchange_rate, 6),
        })


class MarketCurrencyView(APIView):
    """Get currency information for a market."""
    
    permission_classes = [AllowAny]
    
    @extend_schema(
        summary="Get market currency",
        description="Get currency information for a specific market",
        parameters=[
            OpenApiParameter(
                name="market",
                type=OpenApiTypes.STR,
                location=OpenApiParameter.QUERY,
                required=True,
                description="Market code (KG, US)",
            ),
        ],
        responses={
            200: CurrencySerializer,
            400: inline_serializer(
                name="ErrorResponse",
                fields={"error": serializers.CharField()},
            ),
        },
    )
    def get(self, request):
        market = request.query_params.get('market', '').upper()
        
        if market not in ['KG', 'US']:
            return Response(
                {"error": "Invalid market. Must be 'KG' or 'US'"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        currency_info = get_market_currency(market)
        
        # Try to get full currency object
        try:
            if market == 'US':
                currency = Currency.objects.filter(code='USD', is_active=True).first()
            elif market == 'KG':
                currency = Currency.objects.filter(code='KGS', is_active=True).first()
            else:
                currency = Currency.objects.filter(is_base=True, is_active=True).first()
            
            if currency:
                serializer = CurrencySerializer(currency)
                return Response(serializer.data)
        except Exception:
            pass
        
        # Fallback to dictionary
        return Response(currency_info)


class CurrencyUpdateRatesView(APIView):
    """Update exchange rates from external API."""
    
    permission_classes = [IsAuthenticated, IsAdminUser]  # Only admins can update rates
    
    @extend_schema(
        summary="Update exchange rates",
        description="Fetch and update exchange rates from external API. Requires admin authentication.",
        parameters=[
            OpenApiParameter(
                name="api",
                type=OpenApiTypes.STR,
                location=OpenApiParameter.QUERY,
                required=False,
                description="API provider to use: 'exchangerate', 'fixer', or 'currencyapi' (default: exchangerate)",
            ),
            OpenApiParameter(
                name="force",
                type=OpenApiTypes.BOOL,
                location=OpenApiParameter.QUERY,
                required=False,
                description="Force update even if rates were recently updated (default: false)",
            ),
        ],
        responses={
            200: inline_serializer(
                name="CurrencyUpdateResponse",
                fields={
                    "success": serializers.BooleanField(),
                    "message": serializers.CharField(),
                    "updated_count": serializers.IntegerField(),
                },
            ),
            403: OpenApiResponse(description="Forbidden - Admin access required"),
        },
        tags=["currency"],
    )
    def post(self, request):
        """Trigger exchange rate update."""
        api_provider = request.query_params.get('api', 'exchangerate')
        force = request.query_params.get('force', 'false').lower() == 'true'
        
        # Capture command output
        out = StringIO()
        err = StringIO()
        
        try:
            call_command(
                'update_exchange_rates',
                api=api_provider,
                force=force,
                stdout=out,
                stderr=err,
            )
            
            output = out.getvalue()
            error_output = err.getvalue()
            
            # Parse output to get updated count
            updated_count = 0
            if 'Successfully updated' in output:
                try:
                    # Extract number from "Successfully updated X currency exchange rate(s)"
                    import re
                    match = re.search(r'Successfully updated (\d+)', output)
                    if match:
                        updated_count = int(match.group(1))
                except:
                    pass
            
            return Response({
                'success': True,
                'message': 'Exchange rates updated successfully',
                'updated_count': updated_count,
                'output': output,
            }, status=status.HTTP_200_OK)
            
        except Exception as e:
            return Response({
                'success': False,
                'message': f'Failed to update exchange rates: {str(e)}',
                'error': str(e),
                'output': out.getvalue(),
                'error_output': err.getvalue(),
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

