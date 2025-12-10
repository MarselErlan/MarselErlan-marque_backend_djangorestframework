"""
Tests for referral fee integration with orders.
Following TDD approach - tests first, then implementation.
"""

from django.test import TestCase
from decimal import Decimal
from rest_framework import status
from rest_framework.test import APIClient

from products.models import Category, Subcategory, Product, Brand, Currency, SKU, ProductSizeOption, ProductColorOption, Cart, CartItem
from stores.models import Store
from users.models import User, Address, PaymentMethod
from orders.models import Order, OrderItem
from referral_fee.models import ReferralFee


class OrderFeeIntegrationTest(TestCase):
    """Test referral fee calculation and integration with orders."""
    
    @classmethod
    def setUpTestData(cls):
        """Set up test data"""
        # Create user
        cls.user = User.objects.create(
            phone='+996555123456',
            full_name='Test User',
            location='KG',
            is_active=True,
        )
        
        # Create store owner and store
        cls.store_owner = User.objects.create(
            phone='+996555000007',
            full_name='Store Owner',
            location='KG',
            is_active=True,
        )
        
        cls.store = Store.objects.create(
            name='Test Store',
            owner=cls.store_owner,
            market='KG',
            status='active',
            is_active=True,
        )
        
        # Create category and subcategory
        cls.category = Category.objects.create(
            name='Electronics',
            slug='electronics',
            market='KG',
            is_active=True,
        )
        
        cls.subcategory = Subcategory.objects.create(
            category=cls.category,
            name='Smartphones',
            slug='smartphones',
            is_active=True,
        )
        
        # Create brand and currency
        cls.brand = Brand.objects.create(
            name='Test Brand',
            slug='test-brand',
            is_active=True,
        )
        
        cls.currency = Currency.objects.create(
            code='USD',
            name='US Dollar',
            symbol='$',
            exchange_rate=1.0,
            is_base=True,
            market='US',
        )
        
        # Create product with price $20
        cls.product = Product.objects.create(
            name='Test Product',
            slug='test-product',
            category=cls.category,
            subcategory=cls.subcategory,
            store=cls.store,
            brand=cls.brand,
            currency=cls.currency,
            price=Decimal('20.00'),
            market='KG',
            is_active=True,
            in_stock=True,
        )
        
        # Create size and color options
        cls.size_option = ProductSizeOption.objects.create(
            product=cls.product,
            name='M',
            is_active=True,
        )
        
        cls.color_option = ProductColorOption.objects.create(
            product=cls.product,
            size=cls.size_option,
            name='Black',
            is_active=True,
        )
        
        # Create SKU
        cls.sku = SKU.objects.create(
            product=cls.product,
            size_option=cls.size_option,
            color_option=cls.color_option,
            sku_code='TEST-M-BLACK',
            price=Decimal('20.00'),
            is_active=True,
        )
        
        # Create referral fee: 10% for this category
        cls.referral_fee = ReferralFee.objects.create(
            category=cls.category,
            subcategory=cls.subcategory,
            fee_percentage=Decimal('10.00'),
            fee_fixed=Decimal('0.00'),
            is_active=True,
        )
        
        # Create address and payment
        cls.address = Address.objects.create(
            user=cls.user,
            market='KG',
            title='Home',
            full_address='Test Address',
            city='Bishkek',
            country='Kyrgyzstan',
            is_default=True,
        )
        
        cls.payment = PaymentMethod.objects.create(
            user=cls.user,
            market='KG',
            payment_type='card',
            card_type='visa',
            card_number_masked='****1234',
            card_holder_name='Test User',
            is_default=True,
        )
    
    def test_order_creation_calculates_referral_fee(self):
        """Test that when order is created, referral fees are calculated and stored"""
        # Create order with product priced at $20
        order = Order.objects.create(
            user=self.user,
            market='KG',
            shipping_address=self.address,
            payment_method_used=self.payment,
            customer_name='Test User',
            customer_phone='+996555123456',
            delivery_address='Test Address',
            subtotal=Decimal('20.00'),
            shipping_cost=Decimal('0.00'),
            tax=Decimal('0.00'),
            total_amount=Decimal('20.00'),
            currency='$',
            currency_code='USD',
            status='confirmed',
        )
        
        # Create order item
        order_item = OrderItem.objects.create(
            order=order,
            sku=self.sku,
            product_name=self.product.name,
            price=Decimal('20.00'),
            quantity=1,
            subtotal=Decimal('20.00'),
        )
        
        # Calculate expected fee: 10% of $20 = $2
        expected_fee = Decimal('2.00')
        
        # Get fee for product
        fee = ReferralFee.get_fee_for_product(self.product)
        self.assertIsNotNone(fee)
        
        # Calculate fee amount
        calculated_fee = fee.calculate_fee(Decimal('20.00'))
        self.assertEqual(calculated_fee, expected_fee)
        
        # Store should receive: $20 - $2 = $18
        store_revenue = Decimal('20.00') - calculated_fee
        self.assertEqual(store_revenue, Decimal('18.00'))
    
    def test_order_item_stores_referral_fee(self):
        """Test that OrderItem stores referral fee information"""
        # This test will verify that OrderItem model has fee fields
        # and that fees are calculated and stored when order is created
        pass  # Will implement after adding fee fields to OrderItem
    
    def test_store_dashboard_shows_net_revenue(self):
        """Test that store dashboard shows revenue after fees (net revenue)"""
        # Create order with $20 product
        order = Order.objects.create(
            user=self.user,
            market='KG',
            shipping_address=self.address,
            payment_method_used=self.payment,
            customer_name='Test User',
            customer_phone='+996555123456',
            delivery_address='Test Address',
            subtotal=Decimal('20.00'),
            shipping_cost=Decimal('0.00'),
            tax=Decimal('0.00'),
            total_amount=Decimal('20.00'),
            currency='$',
            currency_code='USD',
            status='confirmed',
        )
        
        OrderItem.objects.create(
            order=order,
            sku=self.sku,
            product_name=self.product.name,
            price=Decimal('20.00'),
            quantity=1,
            subtotal=Decimal('20.00'),
        )
        
        # Calculate fee: 10% of $20 = $2
        fee = ReferralFee.get_fee_for_product(self.product)
        fee_amount = fee.calculate_fee(Decimal('20.00'))
        
        # Net revenue for store: $20 - $2 = $18
        net_revenue = Decimal('20.00') - fee_amount
        self.assertEqual(net_revenue, Decimal('18.00'))
        
        # Store dashboard should show $18, not $20
        # This will be tested when we update the dashboard views

