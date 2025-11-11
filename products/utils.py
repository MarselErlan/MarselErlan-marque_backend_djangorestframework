"""
Utility functions for market-based filtering
"""
from django.db.models import Q


def filter_by_market(queryset, user_market):
    """
    Filter queryset by user's market.
    Returns items that match user's market OR are available in all markets.
    
    Args:
        queryset: Django queryset with 'market' field
        user_market: User's market code ('KG', 'US', etc.)
    
    Returns:
        Filtered queryset
    
    Example:
        products = Product.objects.filter(is_active=True)
        products = filter_by_market(products, request.user.location)
    """
    return queryset.filter(Q(market=user_market) | Q(market='ALL'))


def get_user_market_from_phone(phone):
    """
    Determine user's market based on phone number country code.
    
    Args:
        phone: Phone number with country code (e.g., '+996505123456')
    
    Returns:
        Market code ('KG', 'US', etc.)
    
    Example:
        market = get_user_market_from_phone('+996505123456')  # Returns 'KG'
        market = get_user_market_from_phone('+15551234567')   # Returns 'US'
    """
    if phone.startswith('+996'):
        return 'KG'
    elif phone.startswith('+1'):
        return 'US'
    else:
        return 'KG'  # Default to KG for unknown country codes


def get_market_currency(market):
    """
    Get currency information for a market.
    
    Args:
        market: Market code ('KG', 'US')
    
    Returns:
        Dictionary with currency info
    
    Example:
        currency_info = get_market_currency('KG')
        # Returns: {'symbol': 'сом', 'code': 'KGS', 'country': 'Kyrgyzstan'}
    """
    market_currencies = {
        'KG': {
            'symbol': 'сом',
            'code': 'KGS',
            'country': 'Kyrgyzstan',
            'language': 'ru'
        },
        'US': {
            'symbol': '$',
            'code': 'USD',
            'country': 'United States',
            'language': 'en'
        }
    }
    return market_currencies.get(market, market_currencies['KG'])

