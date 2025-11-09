"""
Integration tests for products API endpoints.
"""

from decimal import Decimal

from django.test import TestCase
from rest_framework import status
from rest_framework.test import APIClient

from products.models import (
    Category,
    Product,
    ProductFeature,
    SKU,
    Subcategory,
)
from users.models import User


class ProductAPIViewTests(TestCase):
    """Integration tests covering products catalogue endpoints."""

    @classmethod
    def setUpTestData(cls):
        cls.client = APIClient()

        # Categories and subcategories
        cls.category = Category.objects.create(
            name="Мужчинам",
            slug="men",
            market="KG",
            description="Категория мужских товаров",
            is_active=True,
        )
        cls.other_category = Category.objects.create(
            name="США Категория",
            slug="us-category",
            market="US",
            description="Категория только для рынка США",
            is_active=True,
        )
        cls.subcategory = Subcategory.objects.create(
            category=cls.category,
            name="Футболки",
            slug="t-shirts",
            description="Лучшие футболки",
            is_active=True,
        )
        cls.subcategory_no_products = Subcategory.objects.create(
            category=cls.category,
            name="Джинсы",
            slug="jeans",
            is_active=True,
        )

        # Products & SKUs
        cls.product = Product.objects.create(
            name="Футболка MARQUE",
            slug="marque-tee",
            brand="MARQUE",
            description="Дышащая футболка для спорта",
            price=Decimal("2500.00"),
            original_price=Decimal("3000.00"),
            discount=10,
            market="KG",
            category=cls.category,
            subcategory=cls.subcategory,
            rating=Decimal("4.6"),
            reviews_count=2,
            sales_count=150,
            in_stock=True,
            is_active=True,
            is_best_seller=True,
        )
        cls.product_second = Product.objects.create(
            name="Футболка SPORT",
            slug="sport-tee",
            brand="SPORT",
            description="Футболка для тренировок",
            price=Decimal("3200.00"),
            market="KG",
            category=cls.category,
            subcategory=cls.subcategory,
            rating=Decimal("4.1"),
            reviews_count=1,
            sales_count=90,
            in_stock=True,
            is_active=True,
        )
        cls.product_other_market = Product.objects.create(
            name="USA Hoodie",
            slug="usa-hoodie",
            brand="US BRAND",
            description="Hoodie for US market",
            price=Decimal("4500.00"),
            market="US",
            category=cls.other_category,
            subcategory=None,
            rating=Decimal("4.0"),
            reviews_count=0,
            sales_count=10,
            in_stock=True,
            is_active=True,
        )

        # SKUs for first product
        SKU.objects.create(
            product=cls.product,
            sku_code="MARQUE-S-BLACK",
            size="S",
            color="black",
            price=Decimal("2300.00"),
            original_price=Decimal("2800.00"),
            stock=10,
            is_active=True,
        )
        SKU.objects.create(
            product=cls.product,
            sku_code="MARQUE-M-WHITE",
            size="M",
            color="white",
            price=Decimal("2600.00"),
            original_price=Decimal("3000.00"),
            stock=5,
            is_active=True,
        )

        # SKU for second product
        SKU.objects.create(
            product=cls.product_second,
            sku_code="SPORT-L-RED",
            size="L",
            color="red",
            price=Decimal("3100.00"),
            original_price=Decimal("3400.00"),
            stock=8,
            is_active=True,
        )

        ProductFeature.objects.create(
            product=cls.product,
            feature_text="Материал: Хлопок",
            sort_order=1,
        )

        cls.user = User.objects.create_user(
            phone="+996777123456",
            full_name="Integration User",
            password="password123",
            market="KG",
        )

    def test_products_list_returns_active_products(self):
        """GET /api/v1/products should return active in-stock products with totals."""
        response = self.client.get("/api/v1/products")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 2)
        self.assertEqual(response["X-Total-Count"], "2")
        self.assertEqual(response.data[0]["title"], "Футболка MARQUE")

    def test_products_best_sellers_endpoint(self):
        """GET /api/v1/products/best-sellers should return only best seller products."""
        response = self.client.get("/api/v1/products/best-sellers")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]["slug"], "marque-tee")
        self.assertEqual(response["X-Total-Count"], "1")

    def test_product_search_with_filters(self):
        """Search endpoint should support query and filter parameters."""
        response = self.client.get(
            "/api/v1/products/search",
            {
                "query": "Футболка",
                "sizes": "S",
                "colors": "black",
                "sort_by": "price_asc",
                "page": 1,
                "limit": 10,
            },
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("products", response.data)
        self.assertEqual(response.data["total"], 1)
        self.assertEqual(response.data["products"][0]["slug"], "marque-tee")
        self.assertEqual(response.data["page"], 1)
        self.assertEqual(response.data["limit"], 10)

    def test_product_detail_by_slug(self):
        """Detail endpoint should return structured product payload."""
        response = self.client.get("/api/v1/products/marque-tee")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("available_sizes", response.data)
        self.assertIn("images", response.data)
        self.assertEqual(response.data["slug"], "marque-tee")
        self.assertEqual(response["X-Currency-Code"], "KGS")

    def test_categories_list_returns_product_counts(self):
        """Categories endpoint should expose product counts respecting market filter."""
        response = self.client.get("/api/v1/categories")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["total"], 1)
        category = response.data["categories"][0]
        self.assertEqual(category["slug"], "men")
        self.assertEqual(category["product_count"], 2)

    def test_category_detail_includes_subcategories(self):
        """Category detail endpoint should include subcategories with counts."""
        response = self.client.get("/api/v1/categories/men")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["category"]["slug"], "men")
        self.assertEqual(len(response.data["subcategories"]), 2)
        subcategories = response.data["subcategories"]
        slug_map = {item["slug"]: item for item in subcategories}
        self.assertIn("t-shirts", slug_map)
        self.assertIn("jeans", slug_map)
        self.assertEqual(slug_map["t-shirts"]["product_count"], 2)
        self.assertEqual(slug_map["jeans"]["product_count"], 0)

    def test_category_subcategory_products_endpoint(self):
        """Products endpoint scoped by category and subcategory should include filter metadata."""
        response = self.client.get(
            "/api/v1/categories/men/subcategories/t-shirts/products",
            {
                "sort_by": "price_desc",
                "sizes": "S",
            },
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("filters", response.data)
        self.assertIn("available_sizes", response.data["filters"])
        self.assertIn("price_range", response.data["filters"])
        self.assertEqual(response.data["category"]["slug"], "men")
        self.assertEqual(response.data["subcategory"]["slug"], "t-shirts")
        self.assertGreaterEqual(response.data["total"], 1)
        sizes = response.data["products"][0]["available_sizes"]
        self.assertIn("S", sizes)

    def test_subcategory_products_legacy_endpoint(self):
        """Legacy endpoint without category slug should still resolve products."""
        response = self.client.get("/api/v1/subcategories/t-shirts/products")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["subcategory"]["slug"], "t-shirts")
        self.assertEqual(response.data["category"]["slug"], "men")
        self.assertEqual(response.data["total"], 2)

    def test_market_filter_excludes_other_markets(self):
        """Endpoints should not return products from other markets by default."""
        response = self.client.get("/api/v1/products")
        slugs = {item["slug"] for item in response.data}
        self.assertNotIn("usa-hoodie", slugs)

        # Request US market explicitly
        response_us = self.client.get(
            "/api/v1/products",
            HTTP_X_MARKET="US",
        )
        slugs_us = {item["slug"] for item in response_us.data}
        self.assertIn("usa-hoodie", slugs_us)
        self.assertEqual(response_us["X-Currency-Code"], "USD")

