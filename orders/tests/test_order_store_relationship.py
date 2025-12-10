"""
Tests for Order-Store relationship.
Ensuring orders are properly linked to stores and appear in correct store manager dashboards.
"""

from django.test import TestCase
from django.utils import timezone
from decimal import Decimal
from rest_framework import status
from rest_framework.test import APIClient

from users.models import User, Address, PaymentMethod
from stores.models import Store
from products.models import (
    Product, Category, Brand, Currency, SKU,
    ProductSizeOption, ProductColorOption, Cart, CartItem
)
from orders.models import Order, OrderItem
from store_manager.models import StoreManager


class OrderStoreRelationshipTest(TestCase):
    """Test Order-Store relationship and store manager dashboard visibility."""
    
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
        
        # Create store managers
        cls.manager1 = StoreManager.objects.create(
            user=cls.store_owner1,
            store=cls.store1,
            role='manager',
            can_manage_kg=True,
            can_view_orders=True,
            can_edit_orders=True,
            is_active=True,
        )
        
        cls.manager2 = StoreManager.objects.create(
            user=cls.store_owner2,
            store=cls.store2,
            role='manager',
            can_manage_kg=True,
            can_view_orders=True,
            can_edit_orders=True,
            is_active=True,
        )
        
        # Create customer
        cls.customer = User.objects.create(
            phone='+996555999999',
            full_name='Customer',
            location='KG',
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
            name='Product 1 - Store 1',
            slug='product-1-store-1',
            category=cls.category,
            brand=cls.brand,
            store=cls.store1,
            market='KG',
            price=Decimal('1000.00'),
            currency=cls.currency,
            is_active=True,
            in_stock=True,
        )
        
        # Create products for store2
        cls.product2 = Product.objects.create(
            name='Product 2 - Store 2',
            slug='product-2-store-2',
            category=cls.category,
            brand=cls.brand,
            store=cls.store2,
            market='KG',
            price=Decimal('2000.00'),
            currency=cls.currency,
            is_active=True,
            in_stock=True,
        )
        
        # Create size and color options
        cls.size_option1 = ProductSizeOption.objects.create(
            product=cls.product1,
            name='M',
            is_active=True,
        )
        
        cls.color_option1 = ProductColorOption.objects.create(
            product=cls.product1,
            size=cls.size_option1,
            name='Black',
            is_active=True,
        )
        
        cls.size_option2 = ProductSizeOption.objects.create(
            product=cls.product2,
            name='L',
            is_active=True,
        )
        
        cls.color_option2 = ProductColorOption.objects.create(
            product=cls.product2,
            size=cls.size_option2,
            name='Red',
            is_active=True,
        )
        
        # Create SKUs
        cls.sku1 = SKU.objects.create(
            product=cls.product1,
            size_option=cls.size_option1,
            color_option=cls.color_option1,
            sku_code='PROD1-M-BLACK',
            price=Decimal('1000.00'),
            is_active=True,
        )
        
        cls.sku2 = SKU.objects.create(
            product=cls.product2,
            size_option=cls.size_option2,
            color_option=cls.color_option2,
            sku_code='PROD2-L-RED',
            price=Decimal('2000.00'),
            is_active=True,
        )
        
        # Create address and payment
        cls.address = Address.objects.create(
            user=cls.customer,
            market='KG',
            title='Home',
            full_address='Test Address',
            city='Bishkek',
            country='Kyrgyzstan',
            is_default=True,
        )
        
        cls.payment = PaymentMethod.objects.create(
            user=cls.customer,
            market='KG',
            payment_type='card',
            card_type='visa',
            card_number_masked='****1234',
            card_holder_name='Customer',
            is_default=True,
        )
    
    def setUp(self):
        """Set up test client"""
        self.client = APIClient()
    
    def test_order_with_store1_product_appears_in_store1_dashboard(self):
        """Test that order with product from store1 appears in store1 manager dashboard"""
        # Create order with product from store1
        order = Order.objects.create(
            user=self.customer,
            market='KG',
            shipping_address=self.address,
            payment_method_used=self.payment,
            customer_name='Customer',
            customer_phone='+996555999999',
            delivery_address='Test Address',
            total_amount=Decimal('1000.00'),
            currency='сом',
            status='confirmed',
        )
        
        # Add order item from store1
        OrderItem.objects.create(
            order=order,
            sku=self.sku1,
            product_name=self.product1.name,
            price=Decimal('1000.00'),
            quantity=1,
            subtotal=Decimal('1000.00'),
        )
        
        # Login as store1 manager
        self.client.force_authenticate(user=self.store_owner1)
        
        # Get orders list
        response = self.client.get('/api/v1/store-manager/orders/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Order should appear in store1 dashboard
        orders = response.data.get('orders', [])
        order_ids = [o.get('id') for o in orders]
        self.assertIn(order.id, order_ids)
    
    def test_order_with_store2_product_appears_in_store2_dashboard(self):
        """Test that order with product from store2 appears in store2 manager dashboard"""
        # Create order with product from store2
        order = Order.objects.create(
            user=self.customer,
            market='KG',
            shipping_address=self.address,
            payment_method_used=self.payment,
            customer_name='Customer',
            customer_phone='+996555999999',
            delivery_address='Test Address',
            total_amount=Decimal('2000.00'),
            currency='сом',
            status='confirmed',
        )
        
        # Add order item from store2
        OrderItem.objects.create(
            order=order,
            sku=self.sku2,
            product_name=self.product2.name,
            price=Decimal('2000.00'),
            quantity=1,
            subtotal=Decimal('2000.00'),
        )
        
        # Login as store2 manager
        self.client.force_authenticate(user=self.store_owner2)
        
        # Get orders list
        response = self.client.get('/api/v1/store-manager/orders/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Order should appear in store2 dashboard
        orders = response.data.get('orders', [])
        order_ids = [o.get('id') for o in orders]
        self.assertIn(order.id, order_ids)
    
    def test_order_with_multiple_stores_appears_in_both_dashboards(self):
        """Test that order with products from multiple stores appears in both dashboards"""
        # Create order with products from both stores
        order = Order.objects.create(
            user=self.customer,
            market='KG',
            shipping_address=self.address,
            payment_method_used=self.payment,
            customer_name='Customer',
            customer_phone='+996555999999',
            delivery_address='Test Address',
            total_amount=Decimal('3000.00'),
            currency='сом',
            status='confirmed',
        )
        
        # Add order item from store1
        OrderItem.objects.create(
            order=order,
            sku=self.sku1,
            product_name=self.product1.name,
            price=Decimal('1000.00'),
            quantity=1,
            subtotal=Decimal('1000.00'),
        )
        
        # Add order item from store2
        OrderItem.objects.create(
            order=order,
            sku=self.sku2,
            product_name=self.product2.name,
            price=Decimal('2000.00'),
            quantity=1,
            subtotal=Decimal('2000.00'),
        )
        
        # Login as store1 manager
        self.client.force_authenticate(user=self.store_owner1)
        response1 = self.client.get('/api/v1/store-manager/orders/')
        self.assertEqual(response1.status_code, status.HTTP_200_OK)
        orders1 = response1.data.get('orders', [])
        order_ids1 = [o.get('id') for o in orders1]
        self.assertIn(order.id, order_ids1, "Order should appear in store1 dashboard")
        
        # Login as store2 manager
        self.client.force_authenticate(user=self.store_owner2)
        response2 = self.client.get('/api/v1/store-manager/orders/')
        self.assertEqual(response2.status_code, status.HTTP_200_OK)
        orders2 = response2.data.get('orders', [])
        order_ids2 = [o.get('id') for o in orders2]
        self.assertIn(order.id, order_ids2, "Order should appear in store2 dashboard")
    
    def test_order_without_store_products_not_in_dashboard(self):
        """Test that store manager doesn't see orders without their store's products"""
        # Create order with product from store1
        order = Order.objects.create(
            user=self.customer,
            market='KG',
            shipping_address=self.address,
            payment_method_used=self.payment,
            customer_name='Customer',
            customer_phone='+996555999999',
            delivery_address='Test Address',
            total_amount=Decimal('1000.00'),
            currency='сом',
            status='confirmed',
        )
        
        # Add order item from store1
        OrderItem.objects.create(
            order=order,
            sku=self.sku1,
            product_name=self.product1.name,
            price=Decimal('1000.00'),
            quantity=1,
            subtotal=Decimal('1000.00'),
        )
        
        # Login as store2 manager (should NOT see this order)
        self.client.force_authenticate(user=self.store_owner2)
        
        # Get orders list
        response = self.client.get('/api/v1/store-manager/orders/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Order should NOT appear in store2 dashboard
        orders = response.data.get('orders', [])
        order_ids = [o.get('id') for o in orders]
        self.assertNotIn(order.id, order_ids)
    
    def test_order_detail_shows_correct_store_access(self):
        """Test that store manager can only view order details for their store's orders"""
        # Create order with product from store1
        order = Order.objects.create(
            user=self.customer,
            market='KG',
            shipping_address=self.address,
            payment_method_used=self.payment,
            customer_name='Customer',
            customer_phone='+996555999999',
            delivery_address='Test Address',
            total_amount=Decimal('1000.00'),
            currency='сом',
            status='confirmed',
        )
        
        # Add order item from store1
        OrderItem.objects.create(
            order=order,
            sku=self.sku1,
            product_name=self.product1.name,
            price=Decimal('1000.00'),
            quantity=1,
            subtotal=Decimal('1000.00'),
        )
        
        # Store1 manager should be able to view
        self.client.force_authenticate(user=self.store_owner1)
        response = self.client.get(f'/api/v1/store-manager/orders/{order.id}/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Store2 manager should NOT be able to view
        self.client.force_authenticate(user=self.store_owner2)
        response = self.client.get(f'/api/v1/store-manager/orders/{order.id}/')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertIn('does not belong to your store', response.data.get('error', ''))

