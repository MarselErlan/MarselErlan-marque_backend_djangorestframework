"""
Unit tests for products app serializers.
"""

from decimal import Decimal

from django.test import TestCase

from orders.models import Review
from products.models import (
    Category,
    Product,
    ProductFeature,
    SKU,
    Subcategory,
)
from products.serializers import (
    ProductDetailSerializer,
    ProductListSerializer,
)
from users.models import User


class ProductSerializerTests(TestCase):
    """Unit tests for product serializers."""

    @classmethod
    def setUpTestData(cls):
        cls.category = Category.objects.create(
            name="Мужчинам",
            slug="men",
            market="KG",
            description="Категория для мужчин",
            is_active=True,
        )
        cls.subcategory = Subcategory.objects.create(
            category=cls.category,
            name="Футболки",
            slug="t-shirts",
            description="Летние футболки",
            is_active=True,
        )

        cls.product = Product.objects.create(
            name="Футболка MARQUE",
            slug="marque-tshirt",
            brand="MARQUE",
            description="Дышащая футболка",
            price=Decimal("2500.00"),
            original_price=Decimal("3000.00"),
            discount=10,
            market="KG",
            category=cls.category,
            subcategory=cls.subcategory,
            rating=Decimal("4.5"),
            reviews_count=2,
            sales_count=120,
            in_stock=True,
            is_active=True,
        )

        cls.secondary_product = Product.objects.create(
            name="Футболка SPORT",
            slug="sport-tshirt",
            brand="SPORT",
            description="Спортивная футболка",
            price=Decimal("3500.00"),
            market="KG",
            category=cls.category,
            subcategory=cls.subcategory,
            rating=Decimal("4.0"),
            reviews_count=1,
            sales_count=80,
            in_stock=True,
            is_active=True,
        )

        SKU.objects.create(
            product=cls.product,
            sku_code="MARQUE-S-BLACK",
            size="S",
            color="black",
            price=Decimal("2300.00"),
            original_price=Decimal("2800.00"),
            stock=5,
            variant_image="https://cdn.example.com/tshirts/marque-black-s.jpg",
            is_active=True,
        )
        SKU.objects.create(
            product=cls.product,
            sku_code="MARQUE-M-WHITE",
            size="M",
            color="white",
            price=Decimal("2600.00"),
            original_price=Decimal("3000.00"),
            stock=3,
            variant_image=None,
            is_active=True,
        )
        ProductFeature.objects.create(
            product=cls.product,
            feature_text="Материал: Хлопок",
            sort_order=1,
        )
        ProductFeature.objects.create(
            product=cls.product,
            feature_text="Плотность: 180 г/м²",
            sort_order=2,
        )

        # Reviews (only approved should be serialized)
        cls.user = User.objects.create_user(
            phone="+996555123456",
            full_name="Test User",
            password="password123",
            location="KG",
        )
        Review.objects.create(
            user=cls.user,
            product=cls.product,
            rating=4,
            comment="Отличное качество!",
            is_verified_purchase=True,
            is_approved=True,
        )
        Review.objects.create(
            user=cls.user,
            product=cls.product,
            rating=5,
            comment="Супер!",
            is_verified_purchase=True,
            is_approved=False,  # Should be excluded
        )

    def test_product_list_serializer_price_ranges_and_variants(self):
        """ProductListSerializer should expose aggregated pricing and variant data."""
        serializer = ProductListSerializer(self.product)
        data = serializer.data

        self.assertEqual(data["title"], "Футболка MARQUE")
        self.assertEqual(data["price_min"], 2300.0)
        self.assertEqual(data["price_max"], 2600.0)
        self.assertEqual(data["original_price_min"], 2800.0)
        self.assertEqual(data["original_price_max"], 3000.0)
        self.assertListEqual(data["available_sizes"], ["M", "S"])
        self.assertListEqual(data["available_colors"], ["black", "white"])
        self.assertEqual(data["brand"]["name"], "MARQUE")
        self.assertEqual(data["brand"]["slug"], "marque")

    def test_product_detail_serializer_includes_attributes_reviews_and_similar(self):
        """ProductDetailSerializer should include attributes, reviews, and similar products."""
        serializer = ProductDetailSerializer(self.product, context={"request": None})
        data = serializer.data

        self.assertIn("attributes", data)
        self.assertEqual(data["attributes"]["Материал"], "Хлопок")
        self.assertEqual(data["attributes"]["Бренд"], "MARQUE")

        self.assertIn("reviews", data)
        self.assertEqual(len(data["reviews"]), 1)
        self.assertEqual(data["reviews"][0]["rating"], 4)
        self.assertEqual(data["reviews"][0]["user_name"], "Test User")

        self.assertIn("similar_products", data)
        self.assertGreaterEqual(len(data["similar_products"]), 1)
        self.assertEqual(
            data["similar_products"][0]["title"], "Футболка SPORT"
        )

