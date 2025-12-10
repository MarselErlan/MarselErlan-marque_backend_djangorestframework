"""
Comprehensive tests for Stores app views.
"""

from django.test import TestCase
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIClient
from datetime import timedelta

from stores.models import Store, StoreFollower
from users.models import User
from products.models import Product, Category, Brand, Currency, SKU, ProductSizeOption, ProductColorOption


class StoreViewTests(TestCase):
    """Test suite for Stores API endpoints."""

    @classmethod
    def setUpTestData(cls):
        """Set up test data"""
        # Create users
        cls.owner_kg = User.objects.create(
            phone='+996555123456',
            full_name='Store Owner KG',
            location='KG',
            is_active=True,
        )
        
        cls.owner_us = User.objects.create(
            phone='+15551234567',
            full_name='Store Owner US',
            location='US',
            is_active=True,
        )
        
        cls.user_kg = User.objects.create(
            phone='+996555999999',
            full_name='Regular User KG',
            location='KG',
            is_active=True,
        )
        
        cls.user_us = User.objects.create(
            phone='+15559999999',
            full_name='Regular User US',
            location='US',
            is_active=True,
        )
        
        # Create stores
        cls.store_kg = Store.objects.create(
            name='Azraud Store',
            owner=cls.owner_kg,
            market='KG',
            description='Premium clothing store in Kyrgyzstan',
            status='active',
            is_active=True,
            is_verified=True,
            rating=4.5,
            reviews_count=100,
            orders_count=500,
            products_count=50,
            likes_count=200,
        )
        
        cls.store_us = Store.objects.create(
            name='USA Fashion Store',
            owner=cls.owner_us,
            market='US',
            description='Fashion store in USA',
            status='active',
            is_active=True,
            rating=4.2,
            reviews_count=50,
            orders_count=200,
            products_count=30,
            likes_count=100,
        )
        
        cls.store_all = Store.objects.create(
            name='Global Store',
            owner=cls.owner_kg,
            market='ALL',
            description='Store for all markets',
            status='active',
            is_active=True,
        )
        
        cls.store_inactive = Store.objects.create(
            name='Inactive Store',
            owner=cls.owner_kg,
            market='KG',
            status='active',
            is_active=False,  # Inactive
        )
        
        cls.store_pending = Store.objects.create(
            name='Pending Store',
            owner=cls.owner_kg,
            market='KG',
            status='pending',  # Not active status
            is_active=True,
        )
        
        # Create category and brand for products
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
        
        cls.currency_kg = Currency.objects.create(
            code='KGS',
            name='Kyrgyzstani Som',
            symbol='сом',
            exchange_rate=1.0,
            is_base=True,
            market='KG',
        )
        
        cls.currency_us = Currency.objects.create(
            code='USD',
            name='US Dollar',
            symbol='$',
            exchange_rate=1.0,
            is_base=True,
            market='US',
        )
        
        # Create products for stores
        cls.product_kg = Product.objects.create(
            name='Product KG',
            slug='product-kg',
            category=cls.category,
            brand=cls.brand,
            store=cls.store_kg,
            market='KG',
            price=1000.00,
            currency=cls.currency_kg,
            is_active=True,
            in_stock=True,
        )
        
        cls.product_us = Product.objects.create(
            name='Product US',
            slug='product-us',
            category=cls.category,
            brand=cls.brand,
            store=cls.store_us,
            market='US',
            price=50.00,
            currency=cls.currency_us,
            is_active=True,
            in_stock=True,
        )
        
        cls.product_all = Product.objects.create(
            name='Product ALL',
            slug='product-all',
            category=cls.category,
            brand=cls.brand,
            store=cls.store_all,
            market='ALL',
            price=2000.00,
            currency=cls.currency_kg,
            is_active=True,
            in_stock=True,
        )

    def setUp(self):
        """Set up test client"""
        self.client = APIClient()

    # Store List Tests
    def test_store_list_success(self):
        """Test successful store list retrieval"""
        response = self.client.get('/api/v1/stores/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['success'])
        self.assertIn('stores', response.data)
        self.assertIn('total', response.data)
        
        # Should return active stores only (default market is KG)
        stores = response.data['stores']
        store_slugs = [s['slug'] for s in stores]
        self.assertIn('azraud-store', store_slugs)
        self.assertIn('global-store', store_slugs)  # ALL market included
        # US store not included because default market is KG
        self.assertNotIn('usa-fashion-store', store_slugs)
        self.assertNotIn('inactive-store', store_slugs)
        self.assertNotIn('pending-store', store_slugs)

    def test_store_list_market_filter_kg(self):
        """Test store list with KG market filter"""
        response = self.client.get('/api/v1/stores/?market=KG')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        stores = response.data['stores']
        store_slugs = [s['slug'] for s in stores]
        self.assertIn('azraud-store', store_slugs)
        self.assertIn('global-store', store_slugs)  # ALL market included
        self.assertNotIn('usa-fashion-store', store_slugs)

    def test_store_list_market_filter_us(self):
        """Test store list with US market filter"""
        response = self.client.get('/api/v1/stores/?market=US')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        stores = response.data['stores']
        store_slugs = [s['slug'] for s in stores]
        self.assertIn('usa-fashion-store', store_slugs)
        self.assertIn('global-store', store_slugs)  # ALL market included
        self.assertNotIn('azraud-store', store_slugs)

    def test_store_list_market_header(self):
        """Test store list with X-Market header"""
        response = self.client.get('/api/v1/stores/', HTTP_X_MARKET='US')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        stores = response.data['stores']
        store_slugs = [s['slug'] for s in stores]
        self.assertIn('usa-fashion-store', store_slugs)
        self.assertIn('global-store', store_slugs)

    def test_store_list_authenticated_user_market(self):
        """Test store list uses authenticated user's market"""
        self.client.force_authenticate(user=self.user_kg)
        response = self.client.get('/api/v1/stores/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        stores = response.data['stores']
        store_slugs = [s['slug'] for s in stores]
        self.assertIn('azraud-store', store_slugs)
        self.assertIn('global-store', store_slugs)

    def test_store_list_pagination(self):
        """Test store list pagination"""
        response = self.client.get('/api/v1/stores/?limit=2&offset=0')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['stores']), 2)
        self.assertIn('limit', response.data)
        self.assertIn('offset', response.data)
        self.assertIn('has_more', response.data)

    def test_store_list_contains_expected_fields(self):
        """Test store list contains all expected fields"""
        response = self.client.get('/api/v1/stores/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        store = response.data['stores'][0]
        self.assertIn('id', store)
        self.assertIn('name', store)
        self.assertIn('slug', store)
        self.assertIn('rating', store)
        self.assertIn('reviews_count', store)
        self.assertIn('orders_count', store)
        self.assertIn('products_count', store)
        self.assertIn('likes_count', store)
        self.assertIn('is_verified', store)
        self.assertIn('is_featured', store)
        self.assertIn('market', store)
        self.assertIn('is_following', store)

    # Store Detail Tests
    def test_store_detail_success(self):
        """Test successful store detail retrieval"""
        response = self.client.get(f'/api/v1/stores/{self.store_kg.slug}/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['success'])
        self.assertIn('store', response.data)
        
        store = response.data['store']
        self.assertEqual(store['name'], 'Azraud Store')
        self.assertEqual(store['slug'], 'azraud-store')
        self.assertEqual(store['market'], 'KG')
        self.assertEqual(float(store['rating']), 4.5)

    def test_store_detail_not_found(self):
        """Test store detail with invalid slug"""
        response = self.client.get('/api/v1/stores/non-existent-store/')
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_store_detail_inactive_store(self):
        """Test store detail for inactive store returns 404"""
        response = self.client.get(f'/api/v1/stores/{self.store_inactive.slug}/')
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_store_detail_contains_expected_fields(self):
        """Test store detail contains all expected fields"""
        response = self.client.get(f'/api/v1/stores/{self.store_kg.slug}/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        store = response.data['store']
        self.assertIn('id', store)
        self.assertIn('name', store)
        self.assertIn('slug', store)
        self.assertIn('description', store)
        self.assertIn('email', store)
        self.assertIn('phone', store)
        self.assertIn('website', store)
        self.assertIn('address', store)
        self.assertIn('rating', store)
        self.assertIn('reviews_count', store)
        self.assertIn('orders_count', store)
        self.assertIn('products_count', store)
        self.assertIn('likes_count', store)
        self.assertIn('is_verified', store)
        self.assertIn('is_featured', store)
        self.assertIn('status', store)
        self.assertIn('market', store)
        self.assertIn('owner', store)
        self.assertIn('owner_name', store)
        self.assertIn('is_following', store)
        self.assertIn('created_at', store)
        self.assertIn('updated_at', store)

    def test_store_detail_is_following_false(self):
        """Test is_following is False for unauthenticated user"""
        response = self.client.get(f'/api/v1/stores/{self.store_kg.slug}/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertFalse(response.data['store']['is_following'])

    def test_store_detail_is_following_true(self):
        """Test is_following is True when user follows store"""
        StoreFollower.objects.create(user=self.user_kg, store=self.store_kg)
        self.client.force_authenticate(user=self.user_kg)
        
        response = self.client.get(f'/api/v1/stores/{self.store_kg.slug}/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['store']['is_following'])

    # Store Products Tests
    def test_store_products_success(self):
        """Test successful store products retrieval"""
        response = self.client.get(f'/api/v1/stores/{self.store_kg.slug}/products/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['success'])
        self.assertIn('store', response.data)
        self.assertIn('products', response.data)
        self.assertIn('total', response.data)
        
        products = response.data['products']
        self.assertEqual(len(products), 1)
        self.assertEqual(products[0]['slug'], 'product-kg')

    def test_store_products_not_found(self):
        """Test store products with invalid slug"""
        response = self.client.get('/api/v1/stores/non-existent-store/products/')
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_store_products_market_filter(self):
        """Test store products with market filter"""
        response = self.client.get(f'/api/v1/stores/{self.store_all.slug}/products/?market=KG')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        products = response.data['products']
        self.assertEqual(len(products), 1)
        self.assertEqual(products[0]['slug'], 'product-all')

    def test_store_products_pagination(self):
        """Test store products pagination"""
        # Create more products
        for i in range(5):
            Product.objects.create(
                name=f'Product {i}',
                slug=f'product-{i}',
                category=self.category,
                brand=self.brand,
                store=self.store_kg,
                market='KG',
                price=1000.00,
                currency=self.currency_kg,
                is_active=True,
                in_stock=True,
            )
        
        response = self.client.get(f'/api/v1/stores/{self.store_kg.slug}/products/?limit=3&offset=0')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['products']), 3)
        self.assertIn('has_more', response.data)

    def test_store_products_only_active_in_stock(self):
        """Test store products only returns active and in-stock products"""
        # Create inactive product
        Product.objects.create(
            name='Inactive Product',
            slug='inactive-product',
            category=self.category,
            brand=self.brand,
            store=self.store_kg,
            market='KG',
            price=1000.00,
            currency=self.currency_kg,
            is_active=False,  # Inactive
            in_stock=True,
        )
        
        # Create out of stock product
        Product.objects.create(
            name='Out of Stock Product',
            slug='out-of-stock-product',
            category=self.category,
            brand=self.brand,
            store=self.store_kg,
            market='KG',
            price=1000.00,
            currency=self.currency_kg,
            is_active=True,
            in_stock=False,  # Out of stock
        )
        
        response = self.client.get(f'/api/v1/stores/{self.store_kg.slug}/products/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        products = response.data['products']
        product_slugs = [p['slug'] for p in products]
        self.assertIn('product-kg', product_slugs)
        self.assertNotIn('inactive-product', product_slugs)
        self.assertNotIn('out-of-stock-product', product_slugs)

    # Follow/Unfollow Store Tests
    def test_toggle_follow_store_requires_authentication(self):
        """Test follow store requires authentication"""
        response = self.client.post(f'/api/v1/stores/{self.store_kg.slug}/follow/')
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_toggle_follow_store_follow(self):
        """Test following a store"""
        self.client.force_authenticate(user=self.user_kg)
        # Get initial follower count (actual followers, not likes_count field)
        initial_follower_count = StoreFollower.objects.filter(store=self.store_kg).count()
        self.store_kg.refresh_from_db()
        initial_likes_count = self.store_kg.likes_count
        
        response = self.client.post(f'/api/v1/stores/{self.store_kg.slug}/follow/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['success'])
        self.assertTrue(response.data['is_following'])
        
        # Verify follower was created
        self.assertTrue(StoreFollower.objects.filter(
            user=self.user_kg,
            store=self.store_kg
        ).exists())
        
        # Check that follower count increased
        final_follower_count = StoreFollower.objects.filter(store=self.store_kg).count()
        self.assertEqual(final_follower_count, initial_follower_count + 1)
        
        # The view updates likes_count to match actual follower count
        self.store_kg.refresh_from_db()
        # likes_count should equal the actual follower count
        self.assertEqual(self.store_kg.likes_count, final_follower_count)
        self.assertEqual(response.data['likes_count'], final_follower_count)

    def test_toggle_follow_store_unfollow(self):
        """Test unfollowing a store"""
        # First follow
        StoreFollower.objects.create(user=self.user_kg, store=self.store_kg)
        self.store_kg.refresh_from_db()
        initial_count = self.store_kg.likes_count
        
        self.client.force_authenticate(user=self.user_kg)
        response = self.client.post(f'/api/v1/stores/{self.store_kg.slug}/follow/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['success'])
        self.assertFalse(response.data['is_following'])
        self.assertEqual(response.data['likes_count'], initial_count - 1)
        
        # Verify follower was deleted
        self.assertFalse(StoreFollower.objects.filter(
            user=self.user_kg,
            store=self.store_kg
        ).exists())

    def test_toggle_follow_store_not_found(self):
        """Test follow store with invalid slug"""
        self.client.force_authenticate(user=self.user_kg)
        response = self.client.post('/api/v1/stores/non-existent-store/follow/')
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_toggle_follow_store_inactive_store(self):
        """Test follow inactive store returns 404"""
        self.client.force_authenticate(user=self.user_kg)
        response = self.client.post(f'/api/v1/stores/{self.store_inactive.slug}/follow/')
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    # Store Statistics Tests
    def test_store_statistics_requires_authentication(self):
        """Test store statistics requires authentication"""
        response = self.client.get(f'/api/v1/stores/{self.store_kg.slug}/statistics/')
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_store_statistics_requires_ownership(self):
        """Test store statistics requires store ownership"""
        self.client.force_authenticate(user=self.user_kg)
        response = self.client.get(f'/api/v1/stores/{self.store_kg.slug}/statistics/')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_store_statistics_success(self):
        """Test successful store statistics retrieval"""
        self.client.force_authenticate(user=self.owner_kg)
        response = self.client.get(f'/api/v1/stores/{self.store_kg.slug}/statistics/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['success'])
        self.assertIn('statistics', response.data)
        
        stats = response.data['statistics']
        self.assertIn('rating', stats)
        self.assertIn('reviews_count', stats)
        self.assertIn('orders_count', stats)
        self.assertIn('products_count', stats)
        self.assertIn('likes_count', stats)

    def test_store_statistics_not_found(self):
        """Test store statistics with invalid slug"""
        self.client.force_authenticate(user=self.owner_kg)
        response = self.client.get('/api/v1/stores/non-existent-store/statistics/')
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    # Store Registration Tests
    def test_store_register_requires_authentication(self):
        """Test store registration requires authentication"""
        response = self.client.post('/api/v1/stores/register/', {
            'name': 'New Store',
            'market': 'KG',
        })
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_store_register_success(self):
        """Test successful store registration"""
        self.client.force_authenticate(user=self.user_kg)
        response = self.client.post('/api/v1/stores/register/', {
            'name': 'My New Store',
            'description': 'A new store',
            'market': 'KG',
            'email': 'store@example.com',
            'phone': '+996555111111',
        })
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(response.data['success'])
        self.assertIn('store', response.data)
        self.assertEqual(response.data['store']['name'], 'My New Store')
        self.assertEqual(response.data['store']['market'], 'KG')
        self.assertEqual(response.data['store']['status'], 'pending')
        self.assertEqual(response.data['store']['owner'], self.user_kg.id)

    def test_store_register_validation_error(self):
        """Test store registration with invalid data"""
        self.client.force_authenticate(user=self.user_kg)
        response = self.client.post('/api/v1/stores/register/', {
            'name': '',  # Empty name
            'market': 'INVALID',  # Invalid market
        })
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertFalse(response.data['success'])
        self.assertIn('errors', response.data)

    def test_store_register_missing_required_fields(self):
        """Test store registration with missing required fields"""
        self.client.force_authenticate(user=self.user_kg)
        response = self.client.post('/api/v1/stores/register/', {
            'description': 'Store without name',
        })
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    # Store Update Tests
    def test_store_update_requires_authentication(self):
        """Test store update requires authentication"""
        response = self.client.put(f'/api/v1/stores/{self.store_kg.slug}/update/', {
            'name': 'Updated Name',
        })
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_store_update_requires_ownership(self):
        """Test store update requires store ownership"""
        self.client.force_authenticate(user=self.user_kg)
        response = self.client.put(f'/api/v1/stores/{self.store_kg.slug}/update/', {
            'name': 'Updated Name',
        })
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_store_update_success(self):
        """Test successful store update"""
        self.client.force_authenticate(user=self.owner_kg)
        response = self.client.put(f'/api/v1/stores/{self.store_kg.slug}/update/', {
            'name': 'Updated Store Name',
            'description': 'Updated description',
            'email': 'newemail@example.com',
        })
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['success'])
        self.assertEqual(response.data['store']['name'], 'Updated Store Name')
        self.assertEqual(response.data['store']['description'], 'Updated description')
        self.assertEqual(response.data['store']['email'], 'newemail@example.com')

    def test_store_update_partial(self):
        """Test partial store update"""
        self.client.force_authenticate(user=self.owner_kg)
        response = self.client.put(f'/api/v1/stores/{self.store_kg.slug}/update/', {
            'email': 'onlyemail@example.com',
        })
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.store_kg.refresh_from_db()
        self.assertEqual(self.store_kg.email, 'onlyemail@example.com')
        # Other fields should remain unchanged
        self.assertEqual(self.store_kg.name, 'Azraud Store')

    def test_store_update_not_found(self):
        """Test store update with invalid slug"""
        self.client.force_authenticate(user=self.owner_kg)
        response = self.client.put('/api/v1/stores/non-existent-store/update/', {
            'name': 'Updated Name',
        })
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    # My Stores Tests
    def test_my_stores_requires_authentication(self):
        """Test my stores requires authentication"""
        response = self.client.get('/api/v1/stores/my-stores/')
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_my_stores_success(self):
        """Test successful my stores retrieval"""
        self.client.force_authenticate(user=self.owner_kg)
        response = self.client.get('/api/v1/stores/my-stores/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['success'])
        self.assertIn('stores', response.data)
        self.assertIn('total', response.data)
        
        stores = response.data['stores']
        store_slugs = [s['slug'] for s in stores]
        self.assertIn('azraud-store', store_slugs)
        self.assertIn('global-store', store_slugs)
        self.assertNotIn('usa-fashion-store', store_slugs)  # Owned by different user

    def test_my_stores_empty(self):
        """Test my stores for user with no stores"""
        self.client.force_authenticate(user=self.user_kg)
        response = self.client.get('/api/v1/stores/my-stores/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['total'], 0)
        self.assertEqual(len(response.data['stores']), 0)

