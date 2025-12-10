"""
Tests for store-based dashboard functionality.
Following TDD approach - tests first, then implementation.
"""

from django.test import TestCase
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIClient
from decimal import Decimal

from users.models import User
from stores.models import Store, StoreFollower
from store_manager.models import StoreManager
from products.models import Product, Category, Brand, Currency, SKU, ProductSizeOption, ProductColorOption
from orders.models import Order, OrderItem
from users.models import Address, PaymentMethod


class StoreDashboardTest(TestCase):
    """Test store-based dashboard functionality."""
    
    @classmethod
    def setUpTestData(cls):
        """Set up test data"""
        # Create store owners
        cls.store_owner1 = User.objects.create(
            phone='+996555111111',
            full_name='Store Owner 1',
            location='KG',
            is_active=True,
        )
        
        cls.store_owner2 = User.objects.create(
            phone='+996555222222',
            full_name='Store Owner 2',
            location='KG',
            is_active=True,
        )
        
        # Create stores
        cls.store1 = Store.objects.create(
            name='Store 1',
            owner=cls.store_owner1,
            market='KG',
            status='active',
            is_active=True,
        )
        
        cls.store2 = Store.objects.create(
            name='Store 2',
            owner=cls.store_owner2,
            market='KG',
            status='active',
            is_active=True,
        )
        
        # Create StoreManager linked to store
        cls.manager1 = StoreManager.objects.create(
            user=cls.store_owner1,
            role='manager',
            can_manage_kg=True,
            can_manage_us=False,
            can_view_orders=True,
            can_edit_orders=True,
            can_cancel_orders=True,
            can_view_revenue=True,
            is_active=True,
        )
        
        # Create category, brand, currency
        cls.category = Category.objects.create(
            name='Test Category',
            slug='test-category',
            market='KG',
        )
        
        cls.brand = Brand.objects.create(
            name='Test Brand',
            slug='test-brand',
            is_active=True,
        )
        
        cls.currency = Currency.objects.create(
            code='KGS',
            name='Kyrgyzstani Som',
            symbol='сом',
            exchange_rate=1.0,
            is_base=True,
            market='KG',
        )
        
        # Create products for store1
        cls.product1 = Product.objects.create(
            name='Product 1',
            slug='product-1',
            category=cls.category,
            brand=cls.brand,
            store=cls.store1,
            market='KG',
            price=1000.00,
            currency=cls.currency,
            is_active=True,
            in_stock=True,
        )
        
        cls.product2 = Product.objects.create(
            name='Product 2',
            slug='product-2',
            category=cls.category,
            brand=cls.brand,
            store=cls.store1,
            market='KG',
            price=2000.00,
            currency=cls.currency,
            is_active=True,
            in_stock=True,
        )
        
        # Create product for store2
        cls.product3 = Product.objects.create(
            name='Product 3',
            slug='product-3',
            category=cls.category,
            brand=cls.brand,
            store=cls.store2,
            market='KG',
            price=3000.00,
            currency=cls.currency,
            is_active=True,
            in_stock=True,
        )
        
        # Create customer
        cls.customer = User.objects.create(
            phone='+996555999999',
            full_name='Customer',
            location='KG',
            is_active=True,
        )
        
        # Create address
        cls.address = Address.objects.create(
            user=cls.customer,
            market='KG',
            title='Home',
            full_address='Test Address',
            city='Bishkek',
            country='Kyrgyzstan',
            is_default=True,
        )
        
        # Create payment method
        cls.payment = PaymentMethod.objects.create(
            user=cls.customer,
            market='KG',
            payment_type='card',
            card_type='visa',
            card_number_masked='****1234',
            card_holder_name='Customer',
            is_default=True,
        )
        
        # Create orders for store1
        cls.order1 = Order.objects.create(
            user=cls.customer,
            market='KG',
            shipping_address=cls.address,
            payment_method_used=cls.payment,
            total_amount=Decimal('1000.00'),
            currency='сом',
            status='confirmed',
        )
        
        # Create order items linking to store1 products
        cls.size_option = ProductSizeOption.objects.create(
            product=cls.product1,
            name='M',
            is_active=True,
        )
        
        cls.color_option = ProductColorOption.objects.create(
            product=cls.product1,
            size=cls.size_option,
            name='Black',
            is_active=True,
        )
        
        cls.sku1 = SKU.objects.create(
            product=cls.product1,
            size_option=cls.size_option,
            color_option=cls.color_option,
            sku_code='PROD1-M-BLACK',
            price=Decimal('1000.00'),
            is_active=True,
        )
        
        OrderItem.objects.create(
            order=cls.order1,
            sku=cls.sku1,
            quantity=1,
            price=Decimal('1000.00'),
        )
    
    def setUp(self):
        """Set up test client"""
        self.client = APIClient()
    
    def test_store_manager_sees_only_their_store_orders(self):
        """Test that store manager sees only orders from their store"""
        self.client.force_authenticate(user=self.store_owner1)
        
        response = self.client.get('/api/v1/store-manager/orders/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Should only see orders with products from store1
        orders = response.data.get('orders', [])
        # All orders should be from store1
        for order_data in orders:
            # Verify order contains products from store1
            pass  # Will implement after updating views
    
    def test_store_manager_sees_only_their_store_products(self):
        """Test that store manager sees only products from their store"""
        self.client.force_authenticate(user=self.store_owner1)
        
        # This endpoint doesn't exist yet, but we'll create it
        # response = self.client.get('/api/v1/store-manager/products/')
        # Should only return products from store1
        pass
    
    def test_store_manager_dashboard_stats_for_their_store(self):
        """Test dashboard stats are filtered by store"""
        self.client.force_authenticate(user=self.store_owner1)
        
        response = self.client.get('/api/v1/store-manager/dashboard/stats/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Stats should only include data from store1
        stats = response.data
        # Will verify after updating views
        pass
    
    def test_store_owner_automatically_gets_manager_access(self):
        """Test that store owners automatically get manager access to their store"""
        # Store owner should be able to access dashboard
        self.client.force_authenticate(user=self.store_owner1)
        
        response = self.client.get('/api/v1/store-manager/check-status/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Should return manager status
        self.assertTrue(response.data.get('is_manager', False))

