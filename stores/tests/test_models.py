"""
Unit Tests for Stores App Models
Tests for Store and StoreFollower models
"""

from django.test import TestCase
from django.contrib.auth import get_user_model
from django.utils import timezone
from datetime import timedelta
from stores.models import Store, StoreFollower
from products.models import Product, Category, Brand, Currency
from orders.models import Order, OrderItem, SKU

User = get_user_model()


class StoreModelTest(TestCase):
    """Test Store model"""
    
    @classmethod
    def setUpTestData(cls):
        """Set up test data"""
        cls.owner_kg = User.objects.create(
            phone='+996555123456',
            full_name='Store Owner KG',
            location='KG',
            language='ru',
            is_active=True,
        )
        
        cls.owner_us = User.objects.create(
            phone='+15551234567',
            full_name='Store Owner US',
            location='US',
            language='en',
            is_active=True,
        )
        
        cls.store_kg = Store.objects.create(
            name='Azraud Store',
            owner=cls.owner_kg,
            market='KG',
            description='Premium clothing store in Kyrgyzstan',
            status='active',
            is_active=True,
            is_verified=True,
        )
        
        cls.store_us = Store.objects.create(
            name='USA Fashion Store',
            owner=cls.owner_us,
            market='US',
            description='Fashion store in USA',
            status='active',
            is_active=True,
        )
    
    def test_store_creation(self):
        """Test store can be created"""
        self.assertEqual(Store.objects.count(), 2)
        self.assertEqual(self.store_kg.name, 'Azraud Store')
        self.assertEqual(self.store_kg.owner, self.owner_kg)
        self.assertEqual(self.store_kg.market, 'KG')
    
    def test_store_str(self):
        """Test store string representation"""
        self.assertEqual(str(self.store_kg), 'Azraud Store')
        self.assertEqual(str(self.store_us), 'USA Fashion Store')
    
    def test_store_slug_auto_generation(self):
        """Test store slug is auto-generated from name"""
        store = Store.objects.create(
            name='Test Store Name',
            owner=self.owner_kg,
            market='KG',
        )
        self.assertEqual(store.slug, 'test-store-name')
        self.assertIsNotNone(store.slug)
    
    def test_store_slug_uniqueness(self):
        """Test store slug uniqueness"""
        store1 = Store.objects.create(
            name='Duplicate Store',
            owner=self.owner_kg,
            market='KG',
        )
        store2 = Store.objects.create(
            name='Duplicate Store',
            owner=self.owner_us,
            market='US',
        )
        self.assertNotEqual(store1.slug, store2.slug)
        self.assertTrue(store2.slug.startswith('duplicate-store'))
    
    def test_store_default_values(self):
        """Test store default values"""
        store = Store.objects.create(
            name='New Store',
            owner=self.owner_kg,
            market='KG',
        )
        self.assertEqual(store.status, 'pending')
        self.assertEqual(store.market, 'KG')
        self.assertEqual(store.rating, 0.0)
        self.assertEqual(store.reviews_count, 0)
        self.assertEqual(store.orders_count, 0)
        self.assertEqual(store.products_count, 0)
        self.assertEqual(store.likes_count, 0)
        self.assertFalse(store.is_verified)
        self.assertFalse(store.is_featured)
    
    def test_store_update_statistics(self):
        """Test store statistics update"""
        # Create category and brand
        category = Category.objects.create(
            name='Test Category',
            slug='test-category',
            market='KG',
        )
        brand = Brand.objects.create(
            name='Test Brand',
            slug='test-brand',
            is_active=True,
        )
        currency = Currency.objects.create(
            code='KGS',
            name='Kyrgyzstani Som',
            symbol='сом',
            exchange_rate=1.0,
            is_base=True,
            market='KG',
        )
        
        # Create products for the store
        product1 = Product.objects.create(
            name='Product 1',
            slug='product-1',
            category=category,
            brand=brand,
            store=self.store_kg,
            market='KG',
            price=1000.00,
            currency=currency,
            is_active=True,
            in_stock=True,
        )
        product2 = Product.objects.create(
            name='Product 2',
            slug='product-2',
            category=category,
            brand=brand,
            store=self.store_kg,
            market='KG',
            price=2000.00,
            currency=currency,
            is_active=True,
            in_stock=True,
        )
        
        # Update statistics
        self.store_kg.update_statistics()
        self.store_kg.refresh_from_db()
        
        # Check products count
        self.assertEqual(self.store_kg.products_count, 2)
        
        # Check orders count (should be 0 initially)
        self.assertEqual(self.store_kg.orders_count, 0)
        
        # Check reviews count (should be 0 initially)
        self.assertEqual(self.store_kg.reviews_count, 0)
        self.assertEqual(float(self.store_kg.rating), 0.0)
    
    def test_store_market_filtering(self):
        """Test store market filtering"""
        kg_stores = Store.objects.filter(market='KG')
        us_stores = Store.objects.filter(market='US')
        
        self.assertIn(self.store_kg, kg_stores)
        self.assertIn(self.store_us, us_stores)
        self.assertNotIn(self.store_kg, us_stores)
        self.assertNotIn(self.store_us, kg_stores)
    
    def test_store_status_filtering(self):
        """Test store status filtering"""
        active_stores = Store.objects.filter(status='active', is_active=True)
        self.assertIn(self.store_kg, active_stores)
        self.assertIn(self.store_us, active_stores)
    
    def test_store_contract_dates(self):
        """Test store contract date fields"""
        now = timezone.now()
        future = now + timedelta(days=365)
        
        store = Store.objects.create(
            name='Contract Store',
            owner=self.owner_kg,
            market='KG',
            contract_signed_date=now,
            contract_expiry_date=future,
        )
        
        self.assertIsNotNone(store.contract_signed_date)
        self.assertIsNotNone(store.contract_expiry_date)
        self.assertLess(store.contract_signed_date, store.contract_expiry_date)


class StoreFollowerModelTest(TestCase):
    """Test StoreFollower model"""
    
    @classmethod
    def setUpTestData(cls):
        """Set up test data"""
        cls.user1 = User.objects.create(
            phone='+996555111111',
            full_name='User 1',
            location='KG',
            is_active=True,
        )
        
        cls.user2 = User.objects.create(
            phone='+996555222222',
            full_name='User 2',
            location='KG',
            is_active=True,
        )
        
        cls.owner = User.objects.create(
            phone='+996555999999',
            full_name='Store Owner',
            location='KG',
            is_active=True,
        )
        
        cls.store = Store.objects.create(
            name='Test Store',
            owner=cls.owner,
            market='KG',
            status='active',
            is_active=True,
        )
    
    def test_store_follower_creation(self):
        """Test store follower can be created"""
        follower = StoreFollower.objects.create(
            user=self.user1,
            store=self.store,
        )
        
        self.assertEqual(StoreFollower.objects.count(), 1)
        self.assertEqual(follower.user, self.user1)
        self.assertEqual(follower.store, self.store)
    
    def test_store_follower_str(self):
        """Test store follower string representation"""
        follower = StoreFollower.objects.create(
            user=self.user1,
            store=self.store,
        )
        expected = f"{self.user1.phone} follows {self.store.name}"
        self.assertEqual(str(follower), expected)
    
    def test_store_follower_uniqueness(self):
        """Test user can only follow a store once"""
        StoreFollower.objects.create(
            user=self.user1,
            store=self.store,
        )
        
        # Try to create duplicate
        with self.assertRaises(Exception):  # IntegrityError
            StoreFollower.objects.create(
                user=self.user1,
                store=self.store,
            )
    
    def test_store_follower_updates_likes_count(self):
        """Test following a store updates likes_count"""
        initial_count = self.store.likes_count
        
        follower1 = StoreFollower.objects.create(
            user=self.user1,
            store=self.store,
        )
        self.store.refresh_from_db()
        self.assertEqual(self.store.likes_count, initial_count + 1)
        
        follower2 = StoreFollower.objects.create(
            user=self.user2,
            store=self.store,
        )
        self.store.refresh_from_db()
        self.assertEqual(self.store.likes_count, initial_count + 2)
    
    def test_store_follower_deletion_updates_likes_count(self):
        """Test unfollowing a store updates likes_count"""
        follower1 = StoreFollower.objects.create(
            user=self.user1,
            store=self.store,
        )
        follower2 = StoreFollower.objects.create(
            user=self.user2,
            store=self.store,
        )
        self.store.refresh_from_db()
        self.assertEqual(self.store.likes_count, 2)
        
        # Delete one follower
        follower1.delete()
        self.store.refresh_from_db()
        self.assertEqual(self.store.likes_count, 1)
        
        # Delete remaining follower
        follower2.delete()
        self.store.refresh_from_db()
        self.assertEqual(self.store.likes_count, 0)
    
    def test_multiple_users_can_follow_same_store(self):
        """Test multiple users can follow the same store"""
        StoreFollower.objects.create(user=self.user1, store=self.store)
        StoreFollower.objects.create(user=self.user2, store=self.store)
        
        self.assertEqual(StoreFollower.objects.filter(store=self.store).count(), 2)
        self.assertEqual(self.store.followers.count(), 2)
    
    def test_user_can_follow_multiple_stores(self):
        """Test user can follow multiple stores"""
        store2 = Store.objects.create(
            name='Another Store',
            owner=self.owner,
            market='KG',
            status='active',
            is_active=True,
        )
        
        StoreFollower.objects.create(user=self.user1, store=self.store)
        StoreFollower.objects.create(user=self.user1, store=store2)
        
        self.assertEqual(self.user1.followed_stores.count(), 2)
        # Check through StoreFollower relationship
        followed_stores = [f.store for f in self.user1.followed_stores.all()]
        self.assertIn(self.store, followed_stores)
        self.assertIn(store2, followed_stores)

