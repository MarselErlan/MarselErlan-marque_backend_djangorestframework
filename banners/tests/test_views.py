"""
Comprehensive tests for Banners app views.
"""

from django.test import TestCase
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIClient
from datetime import timedelta

from banners.models import Banner
from users.models import User


class BannerViewTests(TestCase):
    """Test suite for Banners API endpoints."""

    @classmethod
    def setUpTestData(cls):
        # Create user
        cls.user_kg = User.objects.create_user(
            phone="+996555123456",
            password="password123",
            location="KG",
        )
        cls.user_us = User.objects.create_user(
            phone="+15551234567",
            password="password123",
            location="US",
        )

        # Create banners for KG market
        cls.hero_banner_kg = Banner.objects.create(
            title="KG Hero Banner",
            subtitle="KG Hero Subtitle",
            banner_type="hero",
            market="KG",
            is_active=True,
            sort_order=1,
        )
        cls.promo_banner_kg = Banner.objects.create(
            title="KG Promo Banner",
            subtitle="KG Promo Subtitle",
            banner_type="promo",
            market="KG",
            is_active=True,
            sort_order=1,
        )
        cls.category_banner_kg = Banner.objects.create(
            title="KG Category Banner",
            subtitle="KG Category Subtitle",
            banner_type="category",
            market="KG",
            is_active=True,
            sort_order=1,
        )

        # Create banners for US market
        cls.hero_banner_us = Banner.objects.create(
            title="US Hero Banner",
            subtitle="US Hero Subtitle",
            banner_type="hero",
            market="US",
            is_active=True,
            sort_order=1,
        )

        # Create banner for ALL markets
        cls.hero_banner_all = Banner.objects.create(
            title="ALL Markets Hero Banner",
            subtitle="ALL Markets Subtitle",
            banner_type="hero",
            market="ALL",
            is_active=True,
            sort_order=1,
        )

        # Create inactive banner
        cls.inactive_banner = Banner.objects.create(
            title="Inactive Banner",
            banner_type="hero",
            market="KG",
            is_active=False,
            sort_order=1,
        )

        # Create scheduled banner (future)
        cls.future_banner = Banner.objects.create(
            title="Future Banner",
            banner_type="promo",
            market="KG",
            is_active=True,
            start_date=timezone.now() + timedelta(days=1),
            sort_order=1,
        )

        # Create expired banner
        cls.expired_banner = Banner.objects.create(
            title="Expired Banner",
            banner_type="promo",
            market="KG",
            is_active=True,
            end_date=timezone.now() - timedelta(days=1),
            sort_order=1,
        )

    def setUp(self):
        self.client = APIClient()

    def test_banner_list_all_types(self):
        """Test banner list returns all banner types."""
        response = self.client.get("/api/v1/banners")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("hero_banners", response.data)
        self.assertIn("promo_banners", response.data)
        self.assertIn("category_banners", response.data)
        self.assertIn("total", response.data)

    def test_banner_list_market_filter_kg(self):
        """Test banner list filters by KG market."""
        response = self.client.get("/api/v1/banners?market=KG")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # Should include KG banners and ALL banners
        hero_banners = response.data["hero_banners"]
        hero_titles = [b["title"] for b in hero_banners]
        self.assertIn("KG Hero Banner", hero_titles)
        self.assertIn("ALL Markets Hero Banner", hero_titles)
        self.assertNotIn("US Hero Banner", hero_titles)

    def test_banner_list_market_filter_us(self):
        """Test banner list filters by US market."""
        response = self.client.get("/api/v1/banners?market=US")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        hero_banners = response.data["hero_banners"]
        hero_titles = [b["title"] for b in hero_banners]
        self.assertIn("US Hero Banner", hero_titles)
        self.assertIn("ALL Markets Hero Banner", hero_titles)
        self.assertNotIn("KG Hero Banner", hero_titles)

    def test_banner_list_excludes_inactive(self):
        """Test banner list excludes inactive banners."""
        response = self.client.get("/api/v1/banners?market=KG")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        all_banners = (
            response.data["hero_banners"] +
            response.data["promo_banners"] +
            response.data["category_banners"]
        )
        titles = [b["title"] for b in all_banners]
        self.assertNotIn("Inactive Banner", titles)

    def test_banner_list_excludes_future_banners(self):
        """Test banner list excludes future scheduled banners."""
        response = self.client.get("/api/v1/banners?market=KG")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        all_banners = (
            response.data["hero_banners"] +
            response.data["promo_banners"] +
            response.data["category_banners"]
        )
        titles = [b["title"] for b in all_banners]
        self.assertNotIn("Future Banner", titles)

    def test_banner_list_excludes_expired_banners(self):
        """Test banner list excludes expired banners."""
        response = self.client.get("/api/v1/banners?market=KG")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        all_banners = (
            response.data["hero_banners"] +
            response.data["promo_banners"] +
            response.data["category_banners"]
        )
        titles = [b["title"] for b in all_banners]
        self.assertNotIn("Expired Banner", titles)

    def test_banner_list_with_limit(self):
        """Test banner list respects limit parameter."""
        response = self.client.get("/api/v1/banners?market=KG&limit=1")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertLessEqual(len(response.data["hero_banners"]), 1)
        self.assertLessEqual(len(response.data["promo_banners"]), 1)
        self.assertLessEqual(len(response.data["category_banners"]), 1)

    def test_banner_list_authenticated_user_market(self):
        """Test banner list uses authenticated user's market."""
        self.client.force_authenticate(user=self.user_kg)
        response = self.client.get("/api/v1/banners")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        hero_banners = response.data["hero_banners"]
        hero_titles = [b["title"] for b in hero_banners]
        self.assertIn("KG Hero Banner", hero_titles)

    def test_banner_list_x_market_header(self):
        """Test banner list respects X-Market header."""
        response = self.client.get(
            "/api/v1/banners",
            HTTP_X_MARKET="US"
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        hero_banners = response.data["hero_banners"]
        hero_titles = [b["title"] for b in hero_banners]
        self.assertIn("US Hero Banner", hero_titles)

    def test_hero_banners_list(self):
        """Test hero banners endpoint returns only hero banners."""
        response = self.client.get("/api/v1/banners/hero?market=KG")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIsInstance(response.data, list)
        for banner in response.data:
            self.assertEqual(banner["banner_type"], "hero")

    def test_promo_banners_list(self):
        """Test promo banners endpoint returns only promo banners."""
        response = self.client.get("/api/v1/banners/promo?market=KG")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIsInstance(response.data, list)
        for banner in response.data:
            self.assertEqual(banner["banner_type"], "promo")

    def test_category_banners_list(self):
        """Test category banners endpoint returns only category banners."""
        response = self.client.get("/api/v1/banners/category?market=KG")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIsInstance(response.data, list)
        for banner in response.data:
            self.assertEqual(banner["banner_type"], "category")

    def test_hero_banners_with_limit(self):
        """Test hero banners endpoint respects limit."""
        response = self.client.get("/api/v1/banners/hero?market=KG&limit=1")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertLessEqual(len(response.data), 1)

    def test_banner_list_sort_order(self):
        """Test banners are sorted by sort_order."""
        # Create banners with different sort orders
        Banner.objects.create(
            title="First Banner",
            banner_type="hero",
            market="KG",
            is_active=True,
            sort_order=1,
        )
        Banner.objects.create(
            title="Second Banner",
            banner_type="hero",
            market="KG",
            is_active=True,
            sort_order=2,
        )

        response = self.client.get("/api/v1/banners/hero?market=KG")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # First banner should appear before second
        titles = [b["title"] for b in response.data if b["title"] in ["First Banner", "Second Banner"]]
        if len(titles) >= 2:
            self.assertEqual(titles[0], "First Banner")
            self.assertEqual(titles[1], "Second Banner")

    def test_banner_list_all_markets_banner_included(self):
        """Test ALL market banners are included in both markets."""
        response_kg = self.client.get("/api/v1/banners?market=KG")
        response_us = self.client.get("/api/v1/banners?market=US")

        kg_hero_titles = [b["title"] for b in response_kg.data["hero_banners"]]
        us_hero_titles = [b["title"] for b in response_us.data["hero_banners"]]

        self.assertIn("ALL Markets Hero Banner", kg_hero_titles)
        self.assertIn("ALL Markets Hero Banner", us_hero_titles)

