"""
Tests for Order model methods related to store relationships.
"""

from django.test import TestCase
from decimal import Decimal

from users.models import User, Address, PaymentMethod
from stores.models import Store
from products.models import (
    Product, Category, Brand, Currency, SKU,
    ProductSizeOption, ProductColorOption
)
from orders.models import Order, OrderItem


class OrderStoreMethodsTest(TestCase):
    """Test Order model methods for store relationships."""
    
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
        
        # Create products
        cls.product1 = Product.objects.create(
            name='Product 1',
            slug='product-1',
            category=cls.category,
            brand=cls.brand,
            store=cls.store1,
            market='KG',
            price=Decimal('1000.00'),
            currency=cls.currency,
            is_active=True,
            in_stock=True,
        )
        
        cls.product2 = Product.objects.create(
            name='Product 2',
            slug='product-2',
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
    
    def test_get_stores_single_store(self):
        """Test get_stores() returns correct store for single-store order"""
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
        
        OrderItem.objects.create(
            order=order,
            sku=self.sku1,
            product_name=self.product1.name,
            price=Decimal('1000.00'),
            quantity=1,
            subtotal=Decimal('1000.00'),
        )
        
        stores = order.get_stores()
        self.assertEqual(stores.count(), 1)
        self.assertIn(self.store1, stores)
    
    def test_get_stores_multiple_stores(self):
        """Test get_stores() returns all stores for multi-store order"""
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
        
        OrderItem.objects.create(
            order=order,
            sku=self.sku1,
            product_name=self.product1.name,
            price=Decimal('1000.00'),
            quantity=1,
            subtotal=Decimal('1000.00'),
        )
        
        OrderItem.objects.create(
            order=order,
            sku=self.sku2,
            product_name=self.product2.name,
            price=Decimal('2000.00'),
            quantity=1,
            subtotal=Decimal('2000.00'),
        )
        
        stores = order.get_stores()
        self.assertEqual(stores.count(), 2)
        self.assertIn(self.store1, stores)
        self.assertIn(self.store2, stores)
    
    def test_has_store_products_true(self):
        """Test has_store_products() returns True when order has products from store"""
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
        
        OrderItem.objects.create(
            order=order,
            sku=self.sku1,
            product_name=self.product1.name,
            price=Decimal('1000.00'),
            quantity=1,
            subtotal=Decimal('1000.00'),
        )
        
        self.assertTrue(order.has_store_products(self.store1))
        self.assertTrue(order.has_store_products(self.store1.id))
    
    def test_has_store_products_false(self):
        """Test has_store_products() returns False when order doesn't have products from store"""
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
        
        OrderItem.objects.create(
            order=order,
            sku=self.sku1,
            product_name=self.product1.name,
            price=Decimal('1000.00'),
            quantity=1,
            subtotal=Decimal('1000.00'),
        )
        
        self.assertFalse(order.has_store_products(self.store2))
        self.assertFalse(order.has_store_products(self.store2.id))

