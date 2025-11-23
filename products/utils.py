"""
Utility functions for market-based filtering
"""
from django.db.models import Q


def filter_by_market(queryset, user_market):
    """
    Filter queryset by user's market.
    Returns items that match user's market OR are available in all markets.
    
    For a user with market='US', this will return products where:
    - market = 'US' OR market = 'ALL'
    
    For a user with market='KG', this will return products where:
    - market = 'KG' OR market = 'ALL'
    
    Args:
        queryset: Django queryset with 'market' field
        user_market: User's market code ('KG', 'US', etc.)
    
    Returns:
        Filtered queryset
    
    Example:
        products = Product.objects.filter(is_active=True)
        products = filter_by_market(products, 'US')
        # Returns products where market='US' OR market='ALL'
    """
    if not user_market:
        return queryset
    
    # Normalize market to uppercase
    user_market = str(user_market).upper()
    
    # Filter: Show products in user's market AND products available in ALL markets
    # Using OR operator: market = user_market OR market = 'ALL'
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
    from .models import Currency
    
    # Try to get currency from database
    try:
        if market == 'US':
            currency = Currency.objects.filter(code='USD', is_active=True).first()
        elif market == 'KG':
            currency = Currency.objects.filter(code='KGS', is_active=True).first()
        else:
            currency = Currency.objects.filter(is_base=True, is_active=True).first()
        
        if currency:
            return {
                'symbol': currency.symbol,
                'code': currency.code,
                'name': currency.name,
                'exchange_rate': float(currency.exchange_rate),
                'is_base': currency.is_base,
            }
    except Exception:
        pass
    
    # Fallback to hardcoded values
    market_currencies = {
        'KG': {
            'symbol': 'сом',
            'code': 'KGS',
            'name': 'Kyrgyzstani Som',
            'country': 'Kyrgyzstan',
            'language': 'ru',
            'exchange_rate': 89.5,  # Approximate rate to USD
            'is_base': False,
        },
        'US': {
            'symbol': '$',
            'code': 'USD',
            'name': 'US Dollar',
            'country': 'United States',
            'language': 'en',
            'exchange_rate': 1.0,
            'is_base': True,
        }
    }
    return market_currencies.get(market, market_currencies['KG'])


def convert_currency(amount: float, from_currency_code: str, to_currency_code: str) -> float:
    """
    Convert amount from one currency to another.
    
    Args:
        amount: Amount to convert
        from_currency_code: Source currency code (e.g., 'USD', 'KGS')
        to_currency_code: Target currency code (e.g., 'USD', 'KGS')
    
    Returns:
        Converted amount
    
    Example:
        converted = convert_currency(100, 'USD', 'KGS')
        # Returns: 8950.0 (if 1 USD = 89.5 KGS)
    """
    from .models import Currency
    
    if from_currency_code == to_currency_code:
        return amount
    
    try:
        from_currency = Currency.objects.filter(code=from_currency_code, is_active=True).first()
        to_currency = Currency.objects.filter(code=to_currency_code, is_active=True).first()
        
        if not from_currency or not to_currency:
            return amount  # Return original if currencies not found
        
        # Convert to base currency (USD) first, then to target
        # If from_currency is base, exchange_rate = 1.0
        # Amount in base = amount / from_currency.exchange_rate
        # Amount in target = amount_in_base * to_currency.exchange_rate
        
        if from_currency.is_base:
            amount_in_base = amount
        else:
            amount_in_base = float(amount) / float(from_currency.exchange_rate)
        
        if to_currency.is_base:
            return amount_in_base
        else:
            return amount_in_base * float(to_currency.exchange_rate)
    except Exception:
        # Fallback: use hardcoded rates
        rates = {
            'USD': 1.0,
            'KGS': 89.5,
        }
        from_rate = rates.get(from_currency_code, 1.0)
        to_rate = rates.get(to_currency_code, 1.0)
        if from_rate == 0:
            return amount
        return (amount / from_rate) * to_rate

