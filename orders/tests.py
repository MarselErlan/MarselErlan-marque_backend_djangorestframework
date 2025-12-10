"""
Comprehensive tests for Orders app views.
"""

from decimal import Decimal
from django.test import TestCase
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIClient
from django.core.files.uploadedfile import SimpleUploadedFile

from users.models import User, Address, PaymentMethod
from orders.models import Order, OrderItem, Review, ReviewImage
from products.models import (
    Product, Category, Subcategory, Brand, SKU, ProductSizeOption,
    ProductColorOption, Cart, CartItem, Currency
)
from stores.models import Store


class OrderViewTests(TestCase):
    """Test suite for Orders API endpoints."""

    @classmethod
    def setUpTestData(cls):
        # Create user
        cls.user = User.objects.create_user(
            phone="+996555123456",
            password="password123",
            location="KG",
            full_name="Test User",
        )

        # Create currencies
        cls.currency_kgs = Currency.objects.create(
            code='KGS',
            name='Kyrgyzstani Som',
            symbol='сом',
            exchange_rate=1.0,
            is_base=True,
            is_active=True,
            market='KG',
        )

        # Create address
        cls.address = Address.objects.create(
            user=cls.user,
            market="KG",
            title="Home",
            full_address="Test Street 123",
            city="Bishkek",
            country="Kyrgyzstan",
            is_default=True,
        )

        # Create payment method
        cls.payment_method = PaymentMethod.objects.create(
            user=cls.user,
            market="KG",
            payment_type="card",
            card_type="visa",
            card_number_masked="**** **** **** 1234",
            card_holder_name="Test User",
            expiry_month="12",
            expiry_year="2025",
            is_default=True,
        )

        # Create category and product
        cls.category = Category.objects.create(
            name="Test Category",
            slug="test-category",
            market="KG",
            is_active=True,
        )
        cls.brand = Brand.objects.create(
            name="Test Brand",
            slug="test-brand",
            is_active=True,
        )
        
        # Create store
        cls.store_owner = User.objects.create(
            phone='+996555000001',
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
        
        cls.product = Product.objects.create(
            name="Test Product",
            slug="test-product",
            brand=cls.brand,
            store=cls.store,
            category=cls.category,
            price=Decimal("1000.00"),
            currency=cls.currency_kgs,
            market="KG",
            in_stock=True,
            is_active=True,
        )

        # Create size and color options
        cls.size = ProductSizeOption.objects.create(
            product=cls.product,
            name="M",
            sort_order=1,
        )
        cls.color = ProductColorOption.objects.create(
            product=cls.product,
            size=cls.size,
            name="black",
            hex_code="#000000",
        )

        # Create SKU
        cls.sku = SKU.objects.create(
            product=cls.product,
            sku_code="TEST-SKU-001",
            size_option=cls.size,
            color_option=cls.color,
            price=Decimal("1000.00"),
            currency=cls.currency_kgs,
            stock=10,
            is_active=True,
        )

        # Create cart and cart item
        cls.cart = Cart.objects.create(user=cls.user)
        cls.cart_item = CartItem.objects.create(
            cart=cls.cart,
            sku=cls.sku,
            quantity=2,
        )

    def setUp(self):
        self.client = APIClient()

    def test_create_order_from_cart_success(self):
        """Test creating order from cart."""
        self.client.force_authenticate(user=self.user)
        response = self.client.post(
            "/api/v1/orders/create/",
            {
                "use_cart": True,
                "shipping_address_id": self.address.id,
                "payment_method_used_id": self.payment_method.id,
                "customer_name": "Test Customer",
                "customer_phone": "+996555123456",
                "customer_email": "test@example.com",
                "delivery_address": "Test Street 123",
                "delivery_city": "Bishkek",
                "shipping_cost": 150.00,
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIn("id", response.data)
        self.assertIn("order_number", response.data)
        self.assertEqual(response.data["status"], "pending")

        # Verify cart is cleared
        self.cart.refresh_from_db()
        self.assertEqual(self.cart.items.count(), 0)

        # Verify order items were created
        order = Order.objects.get(id=response.data["id"])
        self.assertEqual(order.items.count(), 1)
        order_item = order.items.first()
        self.assertEqual(order_item.quantity, 2)
        self.assertEqual(order_item.product_name, self.product.name)

    def test_create_order_empty_cart(self):
        """Test creating order with empty cart."""
        # Clear cart
        self.cart.items.all().delete()

        self.client.force_authenticate(user=self.user)
        response = self.client.post(
            "/api/v1/orders/create/",
            {
                "use_cart": True,
                "shipping_address_id": self.address.id,
                "customer_name": "Test Customer",
                "customer_phone": "+996555123456",
                "delivery_address": "Test Street 123",
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("error", response.data)

    def test_create_order_invalid_address(self):
        """Test creating order with invalid address ID."""
        self.client.force_authenticate(user=self.user)
        response = self.client.post(
            "/api/v1/orders/create/",
            {
                "use_cart": True,
                "shipping_address_id": 99999,
                "customer_name": "Test Customer",
                "customer_phone": "+996555123456",
                "delivery_address": "Test Street 123",
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("shipping_address_id", response.data)

    def test_create_order_unauthorized(self):
        """Test creating order without authentication."""
        response = self.client.post(
            "/api/v1/orders/create/",
            {
                "use_cart": True,
                "customer_name": "Test Customer",
                "customer_phone": "+996555123456",
                "delivery_address": "Test Street 123",
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_create_order_currency_conversion(self):
        """Test creating order with currency conversion."""
        # Create USD currency
        currency_usd = Currency.objects.create(
            code='USD',
            name='US Dollar',
            symbol='$',
            exchange_rate=89.5,
            is_active=True,
            market='US',
        )

        self.client.force_authenticate(user=self.user)
        response = self.client.post(
            "/api/v1/orders/create/",
            {
                "use_cart": True,
                "shipping_address_id": self.address.id,
                "customer_name": "Test Customer",
                "customer_phone": "+996555123456",
                "delivery_address": "Test Street 123",
                "currency_code": "USD",
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        order = Order.objects.get(id=response.data["id"])
        self.assertEqual(order.currency_code, "USD")
        self.assertEqual(order.currency, "$")

    def test_create_review_success(self):
        """Test creating review for an order product."""
        # Create an order first
        order = Order.objects.create(
            user=self.user,
            market="KG",
            customer_name="Test Customer",
            customer_phone="+996555123456",
            delivery_address="Test Address",
            subtotal=Decimal("1000.00"),
            shipping_cost=Decimal("150.00"),
            total_amount=Decimal("1150.00"),
            currency="сом",
            currency_code="KGS",
            status="delivered",
        )
        OrderItem.objects.create(
            order=order,
            sku=self.sku,
            product_name=self.product.name,
            product_brand=self.brand.name,
            size="M",
            color="black",
            price=Decimal("1000.00"),
            quantity=1,
            subtotal=Decimal("1000.00"),
        )

        self.client.force_authenticate(user=self.user)
        response = self.client.post(
            "/api/v1/orders/review/create/",
            {
                "order_id": order.id,
                "product_id": self.product.id,
                "rating": 5,
                "comment": "Great product!",
                "title": "Excellent",
            },
            format="multipart",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIn("id", response.data)
        self.assertEqual(response.data["rating"], 5)
        self.assertEqual(response.data["comment"], "Great product!")

        # Verify review was created
        review = Review.objects.get(id=response.data["id"])
        self.assertEqual(review.user, self.user)
        self.assertEqual(review.product, self.product)
        self.assertEqual(review.order, order)
        self.assertTrue(review.is_verified_purchase)

    def test_create_review_with_images(self):
        """Test creating review with images."""
        # Create an order
        order = Order.objects.create(
            user=self.user,
            market="KG",
            customer_name="Test Customer",
            customer_phone="+996555123456",
            delivery_address="Test Address",
            subtotal=Decimal("1000.00"),
            shipping_cost=Decimal("150.00"),
            total_amount=Decimal("1150.00"),
            currency="сом",
            currency_code="KGS",
            status="delivered",
        )
        OrderItem.objects.create(
            order=order,
            sku=self.sku,
            product_name=self.product.name,
            product_brand=self.brand.name,
            size="M",
            color="black",
            price=Decimal("1000.00"),
            quantity=1,
            subtotal=Decimal("1000.00"),
        )

        # Create test image
        gif_bytes = (
            b"GIF89a\x01\x00\x01\x00\x80\x00\x00\x00\x00\x00"
            b"\xff\xff\xff!\xf9\x04\x01\n\x00\x01\x00,\x00\x00\x00"
            b"\x00\x01\x00\x01\x00\x00\x02\x02D\x01\x00;"
        )
        image_file = SimpleUploadedFile(
            "test_image.gif",
            gif_bytes,
            content_type="image/gif",
        )

        self.client.force_authenticate(user=self.user)
        response = self.client.post(
            "/api/v1/orders/review/create/",
            {
                "order_id": order.id,
                "product_id": self.product.id,
                "rating": 4,
                "comment": "Good product with images",
                "images": [image_file],
            },
            format="multipart",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        review = Review.objects.get(id=response.data["id"])
        self.assertEqual(review.images.count(), 1)

    def test_create_review_duplicate(self):
        """Test creating duplicate review fails."""
        # Create an order and existing review
        order = Order.objects.create(
            user=self.user,
            market="KG",
            customer_name="Test Customer",
            customer_phone="+996555123456",
            delivery_address="Test Address",
            subtotal=Decimal("1000.00"),
            shipping_cost=Decimal("150.00"),
            total_amount=Decimal("1150.00"),
            currency="сом",
            currency_code="KGS",
            status="delivered",
        )
        OrderItem.objects.create(
            order=order,
            sku=self.sku,
            product_name=self.product.name,
            product_brand=self.brand.name,
            size="M",
            color="black",
            price=Decimal("1000.00"),
            quantity=1,
            subtotal=Decimal("1000.00"),
        )
        Review.objects.create(
            user=self.user,
            product=self.product,
            order=order,
            rating=5,
            comment="First review",
        )

        self.client.force_authenticate(user=self.user)
        response = self.client.post(
            "/api/v1/orders/review/create/",
            {
                "order_id": order.id,
                "product_id": self.product.id,
                "rating": 4,
                "comment": "Second review",
            },
            format="multipart",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        # The view checks for duplicate and returns error message
        # Check if error is in response (could be in different formats)
        response_str = str(response.data).lower()
        self.assertTrue(
            "error" in response.data or
            "already reviewed" in response_str or
            "already exists" in response_str or
            "unique" in response_str
        )

    def test_create_review_invalid_order(self):
        """Test creating review with invalid order ID."""
        self.client.force_authenticate(user=self.user)
        response = self.client.post(
            "/api/v1/orders/review/create/",
            {
                "order_id": 99999,
                "product_id": self.product.id,
                "rating": 5,
                "comment": "Test",
            },
            format="multipart",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("order_id", response.data)

    def test_create_review_invalid_rating(self):
        """Test creating review with invalid rating."""
        order = Order.objects.create(
            user=self.user,
            market="KG",
            customer_name="Test Customer",
            customer_phone="+996555123456",
            delivery_address="Test Address",
            subtotal=Decimal("1000.00"),
            shipping_cost=Decimal("150.00"),
            total_amount=Decimal("1150.00"),
            currency="сом",
            currency_code="KGS",
            status="delivered",
        )

        self.client.force_authenticate(user=self.user)
        response = self.client.post(
            "/api/v1/orders/review/create/",
            {
                "order_id": order.id,
                "product_id": self.product.id,
                "rating": 6,  # Invalid: should be 1-5
                "comment": "Test",
            },
            format="multipart",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_create_review_invalid_image_type(self):
        """Test creating review with invalid image file type."""
        order = Order.objects.create(
            user=self.user,
            market="KG",
            customer_name="Test Customer",
            customer_phone="+996555123456",
            delivery_address="Test Address",
            subtotal=Decimal("1000.00"),
            shipping_cost=Decimal("150.00"),
            total_amount=Decimal("1150.00"),
            currency="сом",
            currency_code="KGS",
            status="delivered",
        )

        # Create invalid file (not an image)
        text_file = SimpleUploadedFile(
            "test.txt",
            b"not an image",
            content_type="text/plain",
        )

        self.client.force_authenticate(user=self.user)
        response = self.client.post(
            "/api/v1/orders/review/create/",
            {
                "order_id": order.id,
                "product_id": self.product.id,
                "rating": 5,
                "comment": "Test",
                "images": [text_file],
            },
            format="multipart",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("error", response.data)
