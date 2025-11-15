"""
Integration tests for products API endpoints.
"""

from decimal import Decimal

from django.core.files.storage import default_storage
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from rest_framework import status
from rest_framework.test import APIClient

from products.models import (
    Cart,
    Category,
    Product,
    ProductFeature,
    ProductSizeOption,
    ProductColorOption,
    SKU,
    Subcategory,
    Wishlist,
)
from users.models import User


class ProductAPIViewTests(TestCase):
    """Integration tests covering products catalogue endpoints."""

    @classmethod
    def setUpTestData(cls):
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

        # Size/color options for first product
        cls.size_s = ProductSizeOption.objects.create(product=cls.product, name="S", sort_order=1)
        cls.size_m = ProductSizeOption.objects.create(product=cls.product, name="M", sort_order=2)
        cls.color_s_black = ProductColorOption.objects.create(product=cls.product, size=cls.size_s, name="black")
        cls.color_m_white = ProductColorOption.objects.create(product=cls.product, size=cls.size_m, name="white")

        # Size/color options for second product
        cls.size_l_second = ProductSizeOption.objects.create(product=cls.product_second, name="L", sort_order=1)
        cls.color_l_red = ProductColorOption.objects.create(product=cls.product_second, size=cls.size_l_second, name="red")

        # SKUs for products
        SKU.objects.create(
            product=cls.product,
            sku_code="MARQUE-S-BLACK",
            size_option=cls.size_s,
            color_option=cls.color_s_black,
            price=Decimal("2300.00"),
            original_price=Decimal("2800.00"),
            stock=10,
            is_active=True,
        )
        SKU.objects.create(
            product=cls.product,
            sku_code="MARQUE-M-WHITE",
            size_option=cls.size_m,
            color_option=cls.color_m_white,
            price=Decimal("2600.00"),
            original_price=Decimal("3000.00"),
            stock=5,
            is_active=True,
        )

        SKU.objects.create(
            product=cls.product_second,
            sku_code="SPORT-L-RED",
            size_option=cls.size_l_second,
            color_option=cls.color_l_red,
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
            location="KG",
        )

        cls.sku1 = SKU.objects.filter(product=cls.product, sku_code="MARQUE-S-BLACK").first()
        cls.sku2 = SKU.objects.filter(product=cls.product_second, sku_code="SPORT-L-RED").first()

    def setUp(self):
        self.client = APIClient()

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

    def test_product_image_upload_requires_authentication(self):
        """Uploading without credentials should be rejected."""
        response = self.client.post("/api/v1/upload/image", format="multipart")
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_product_image_upload_success(self):
        """Authenticated users can upload images and receive URL + metadata."""
        self.client.force_authenticate(user=self.user)
        gif_bytes = (
            b"GIF89a\x01\x00\x01\x00\x80\x00\x00\x00\x00\x00"
            b"\xff\xff\xff!\xf9\x04\x01\n\x00\x01\x00,\x00\x00\x00"
            b"\x00\x01\x00\x01\x00\x00\x02\x02D\x01\x00;"
        )
        image_file = SimpleUploadedFile(
            "sample.gif",
            gif_bytes,
            content_type="image/gif",
        )

        response = self.client.post(
            "/api/v1/upload/image",
            {"image": image_file, "folder": "catalog"},
            format="multipart",
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(response.data["success"])
        self.assertIn("url", response.data)

        saved_path = response.data["path"]
        self.assertTrue(default_storage.exists(saved_path))

        # Clean up uploaded file
        default_storage.delete(saved_path)
        self.client.force_authenticate(user=None)

    def test_cart_get_creates_empty_cart(self):
        """Cart get endpoint should return empty cart for new user."""
        response = self.client.post(
            "/api/v1/cart/get",
            {"user_id": self.user.id},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["user_id"], self.user.id)
        self.assertEqual(response.data["items"], [])
        self.assertEqual(response.data["total_items"], 0)
        self.assertEqual(response.data["total_price"], 0.0)

    def test_cart_add_and_update_flow(self):
        """Adding, updating, and removing items should adjust cart totals."""
        response = self.client.post(
            "/api/v1/cart/add",
            {"user_id": self.user.id, "sku_id": self.sku1.id, "quantity": 2},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["total_items"], 2)
        self.assertAlmostEqual(response.data["total_price"], float(self.sku1.price) * 2)
        item_payload = response.data["items"][0]
        item_id = item_payload["id"]
        self.assertEqual(item_payload["sku_id"], self.sku1.id)
        self.assertEqual(item_payload["product_id"], self.product.id)
        self.assertEqual(item_payload["quantity"], 2)
        self.assertEqual(item_payload["size"], self.sku1.size)
        self.assertEqual(item_payload["color"], self.sku1.color)
        self.assertIn("image", item_payload)

        # Update quantity
        response = self.client.post(
            "/api/v1/cart/update",
            {"user_id": self.user.id, "cart_item_id": item_id, "quantity": 3},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["total_items"], 3)
        self.assertAlmostEqual(response.data["total_price"], float(self.sku1.price) * 3)

        # Remove item
        response = self.client.post(
            "/api/v1/cart/remove",
            {"user_id": self.user.id, "cart_item_id": item_id},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["total_items"], 0)
        self.assertEqual(response.data["items"], [])
        self.assertEqual(response.data["total_price"], 0.0)

    def test_cart_clear_endpoint(self):
        """Clear endpoint should remove all items."""
        self.client.post(
            "/api/v1/cart/add",
            {"user_id": self.user.id, "sku_id": self.sku1.id, "quantity": 1},
            format="json",
        )
        self.client.post(
            "/api/v1/cart/add",
            {"user_id": self.user.id, "sku_id": self.sku2.id, "quantity": 2},
            format="json",
        )
        response = self.client.post(
            "/api/v1/cart/clear",
            {"user_id": self.user.id},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["total_items"], 0)
        self.assertEqual(response.data["items"], [])
        self.assertEqual(response.data["total_price"], 0.0)

    def test_wishlist_add_and_remove(self):
        """Wishlist endpoints should add and remove products."""
        response = self.client.post(
            "/api/v1/wishlist/add",
            {"user_id": self.user.id, "product_id": self.product.id},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["items"]), 1)
        wishlist_item = response.data["items"][0]
        self.assertEqual(wishlist_item["product"]["id"], self.product.id)
        self.assertEqual(wishlist_item["product"]["brand"]["name"], self.product.brand)
        self.assertIn("price_min", wishlist_item["product"])
        self.assertIn("available_sizes", wishlist_item["product"])

        response = self.client.post(
            "/api/v1/wishlist/remove",
            {"user_id": self.user.id, "product_id": self.product.id},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["items"]), 0)

    def test_wishlist_clear(self):
        """Clearing wishlist should return success and empty items."""
        self.client.post(
            "/api/v1/wishlist/add",
            {"user_id": self.user.id, "product_id": self.product.id},
            format="json",
        )
        self.client.post(
            "/api/v1/wishlist/add",
            {"user_id": self.user.id, "product_id": self.product_second.id},
            format="json",
        )
        response = self.client.post(
            "/api/v1/wishlist/clear",
            {"user_id": self.user.id},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data["success"])
        self.assertEqual(len(response.data["items"]), 0)

    def test_wishlist_get_returns_structure(self):
        """Wishlist get should include expected fields even when empty."""
        response = self.client.post(
            "/api/v1/wishlist/get",
            {"user_id": self.user.id},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("items", response.data)
        self.assertEqual(response.data["items"], [])

    def test_cart_requires_user_id(self):
        """Cart endpoints should validate payloads."""
        response = self.client.post("/api/v1/cart/get", {}, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_wishlist_add_requires_product_id(self):
        """Wishlist add should reject missing product id."""
        response = self.client.post(
            "/api/v1/wishlist/add",
            {"user_id": self.user.id},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

