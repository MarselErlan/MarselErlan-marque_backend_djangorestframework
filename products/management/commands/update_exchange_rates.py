"""
Management command to update exchange rates from external API
"""
from django.core.management.base import BaseCommand
from django.utils import timezone
from decimal import Decimal
import requests
import os
from products.models import Currency


class Command(BaseCommand):
    help = 'Update exchange rates from external API'

    def add_arguments(self, parser):
        parser.add_argument(
            '--api',
            type=str,
            default='exchangerate',
            choices=['exchangerate', 'fixer', 'currencyapi'],
            help='Exchange rate API to use (default: exchangerate)',
        )
        parser.add_argument(
            '--force',
            action='store_true',
            help='Force update even if rates were recently updated',
        )

    def handle(self, *args, **options):
        api_provider = options['api']
        force = options['force']
        
        self.stdout.write(self.style.SUCCESS(f'Fetching exchange rates from {api_provider} API...'))
        
        try:
            if api_provider == 'exchangerate':
                rates = self.fetch_exchangerate_api()
            elif api_provider == 'fixer':
                rates = self.fetch_fixer_api()
            elif api_provider == 'currencyapi':
                rates = self.fetch_currencyapi_api()
            else:
                self.stdout.write(self.style.ERROR(f'Unknown API provider: {api_provider}'))
                return
            
            if not rates:
                self.stdout.write(self.style.ERROR('Failed to fetch exchange rates'))
                return
            
            # Update currencies
            updated_count = 0
            for currency_code, rate in rates.items():
                try:
                    currency = Currency.objects.get(code=currency_code, is_active=True)
                    
                    # Skip base currency (should always be 1.0)
                    if currency.is_base:
                        self.stdout.write(
                            self.style.WARNING(
                                f'Skipping {currency_code} - base currency rate is always 1.0'
                            )
                        )
                        continue
                    
                    # Skip if not forced and recently updated (within last hour)
                    if not force and currency.updated_at:
                        time_diff = timezone.now() - currency.updated_at
                        if time_diff.total_seconds() < 3600:  # 1 hour
                            self.stdout.write(
                                self.style.WARNING(
                                    f'Skipping {currency_code} - updated recently ({time_diff.seconds // 60} minutes ago)'
                                )
                            )
                            continue
                    
                    # Update exchange rate
                    old_rate = currency.exchange_rate
                    currency.exchange_rate = Decimal(str(rate))
                    currency.save()
                    
                    updated_count += 1
                    self.stdout.write(
                        self.style.SUCCESS(
                            f'Updated {currency_code}: {old_rate} -> {currency.exchange_rate}'
                        )
                    )
                except Currency.DoesNotExist:
                    self.stdout.write(
                        self.style.WARNING(f'Currency {currency_code} not found in database, skipping...')
                    )
                except Exception as e:
                    self.stdout.write(
                        self.style.ERROR(f'Error updating {currency_code}: {str(e)}')
                    )
            
            self.stdout.write(
                self.style.SUCCESS(f'\nSuccessfully updated {updated_count} currency exchange rate(s)')
            )
            
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Error fetching exchange rates: {str(e)}'))
            raise

    def fetch_exchangerate_api(self):
        """
        Fetch exchange rates from exchangerate-api.com (free tier: 1500 requests/month)
        No API key required for basic usage
        """
        try:
            # Get base currency (USD)
            base_currency = Currency.objects.filter(is_base=True, is_active=True).first()
            if not base_currency:
                self.stdout.write(self.style.WARNING('No base currency found, defaulting to USD'))
                base_code = 'USD'
            else:
                base_code = base_currency.code
            
            # Get all active currencies except base (base currency rate is always 1.0)
            currencies = Currency.objects.filter(is_active=True).exclude(is_base=True)
            currency_codes = list(currencies.values_list('code', flat=True))
            
            # Don't try to update base currency
            if base_code in currency_codes:
                currency_codes.remove(base_code)
            
            if not currency_codes:
                self.stdout.write(self.style.WARNING('No currencies to update'))
                return {}
            
            # Fetch rates from API
            url = f'https://api.exchangerate-api.com/v4/latest/{base_code}'
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            rates = {}
            for code in currency_codes:
                if code in data.get('rates', {}):
                    # API returns rate as: 1 base_currency = X target_currency
                    # We need: 1 target_currency = X base_currency
                    # So we invert: 1 / rate
                    api_rate = data['rates'][code]
                    if api_rate and api_rate > 0:
                        # For KGS: if 1 USD = 89 KGS, then 1 KGS = 1/89 USD
                        # But our model stores: 1 USD = exchange_rate of this currency
                        # So we keep the API rate as-is
                        rates[code] = api_rate
            
            return rates
            
        except requests.RequestException as e:
            self.stdout.write(self.style.ERROR(f'API request failed: {str(e)}'))
            return {}
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Error parsing API response: {str(e)}'))
            return {}

    def fetch_fixer_api(self):
        """
        Fetch exchange rates from fixer.io (requires API key)
        Free tier: 100 requests/month
        """
        api_key = os.getenv('FIXER_API_KEY')
        if not api_key:
            self.stdout.write(
                self.style.WARNING('FIXER_API_KEY not set, skipping Fixer API')
            )
            return {}
        
        try:
            base_currency = Currency.objects.filter(is_base=True, is_active=True).first()
            base_code = base_currency.code if base_currency else 'USD'
            
            currencies = Currency.objects.filter(is_active=True).exclude(is_base=True)
            currency_codes = ','.join(currencies.values_list('code', flat=True))
            
            url = f'http://data.fixer.io/api/latest'
            params = {
                'access_key': api_key,
                'base': base_code,
                'symbols': currency_codes,
            }
            
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            if not data.get('success', False):
                self.stdout.write(self.style.ERROR(f'Fixer API error: {data.get("error", "Unknown error")}'))
                return {}
            
            rates = {}
            for code, rate in data.get('rates', {}).items():
                if rate and rate > 0:
                    rates[code] = rate
            
            return rates
            
        except requests.RequestException as e:
            self.stdout.write(self.style.ERROR(f'Fixer API request failed: {str(e)}'))
            return {}
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Error parsing Fixer API response: {str(e)}'))
            return {}

    def fetch_currencyapi_api(self):
        """
        Fetch exchange rates from currencyapi.net (requires API key)
        Free tier: 300 requests/month
        """
        api_key = os.getenv('CURRENCYAPI_KEY')
        if not api_key:
            self.stdout.write(
                self.style.WARNING('CURRENCYAPI_KEY not set, skipping CurrencyAPI')
            )
            return {}
        
        try:
            base_currency = Currency.objects.filter(is_base=True, is_active=True).first()
            base_code = base_currency.code if base_currency else 'USD'
            
            currencies = Currency.objects.filter(is_active=True).exclude(is_base=True)
            currency_codes = list(currencies.values_list('code', flat=True))
            
            url = f'https://api.currencyapi.com/v3/latest'
            headers = {
                'apikey': api_key,
            }
            params = {
                'base_currency': base_code,
                'currencies': ','.join(currency_codes),
            }
            
            response = requests.get(url, headers=headers, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            rates = {}
            for code, rate_data in data.get('data', {}).items():
                if 'value' in rate_data:
                    rate = rate_data['value']
                    if rate and rate > 0:
                        rates[code] = rate
            
            return rates
            
        except requests.RequestException as e:
            self.stdout.write(self.style.ERROR(f'CurrencyAPI request failed: {str(e)}'))
            return {}
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Error parsing CurrencyAPI response: {str(e)}'))
            return {}

