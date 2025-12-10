"""
Unit Tests for Stores App Serializers
Tests for StoreListSerializer and StoreDetailSerializer
"""

from django.test import TestCase
from django.contrib.auth import get_user_model
from rest_framework.test import APIRequestFactory
from stores.serializers import StoreListSerializer, StoreDetailSerializer
from stores.models import Store, StoreFollower

User = get_user_model()


class StoreListSerializerTest(TestCase):
    """Test StoreListSerializer"""
    
    @classmethod
    def setUpTestData(cls):
        """Set up test data"""
        cls.owner = User.objects.create(
            phone='+996555123456',
            full_name='Store Owner',
            location='KG',
            is_active=True,
        )
        
        cls.store = Store.objects.create(
            name='Test Store',
            owner=cls.owner,
            market='KG',
            description='Test store description',
            status='active',
            is_active=True,
            is_verified=True,
            is_featured=True,
            rating=4.5,
            reviews_count=100,
            orders_count=500,
            products_count=50,
            likes_count=200,
        )
        
        cls.factory = APIRequestFactory()
    
    def test_store_list_serializer_contains_expected_fields(self):
        """Test serializer contains all expected fields"""
        request = self.factory.get('/api/v1/stores/')
        # Add AnonymousUser to request for serializer
        from django.contrib.auth.models import AnonymousUser
        request.user = AnonymousUser()
        serializer = StoreListSerializer(instance=self.store, context={'request': request})
        data = serializer.data
        
        self.assertIn('id', data)
        self.assertIn('name', data)
        self.assertIn('slug', data)
        self.assertIn('logo', data)
        self.assertIn('logo_url', data)
        self.assertIn('cover_image', data)
        self.assertIn('cover_image_url', data)
        self.assertIn('rating', data)
        self.assertIn('reviews_count', data)
        self.assertIn('orders_count', data)
        self.assertIn('products_count', data)
        self.assertIn('likes_count', data)
        self.assertIn('is_verified', data)
        self.assertIn('is_featured', data)
        self.assertIn('market', data)
        self.assertIn('is_following', data)
    
    def test_store_list_serializer_data_values(self):
        """Test serializer returns correct data values"""
        request = self.factory.get('/api/v1/stores/')
        from django.contrib.auth.models import AnonymousUser
        request.user = AnonymousUser()
        serializer = StoreListSerializer(instance=self.store, context={'request': request})
        data = serializer.data
        
        self.assertEqual(data['name'], 'Test Store')
        self.assertEqual(data['slug'], 'test-store')
        self.assertEqual(float(data['rating']), 4.5)
        self.assertEqual(data['reviews_count'], 100)
        self.assertEqual(data['orders_count'], 500)
        self.assertEqual(data['products_count'], 50)
        self.assertEqual(data['likes_count'], 200)
        self.assertTrue(data['is_verified'])
        self.assertTrue(data['is_featured'])
        self.assertEqual(data['market'], 'KG')
    
    def test_store_list_serializer_is_following_false(self):
        """Test is_following returns False for unauthenticated user"""
        request = self.factory.get('/api/v1/stores/')
        from django.contrib.auth.models import AnonymousUser
        request.user = AnonymousUser()
        serializer = StoreListSerializer(instance=self.store, context={'request': request})
        data = serializer.data
        
        self.assertFalse(data['is_following'])
    
    def test_store_list_serializer_is_following_true(self):
        """Test is_following returns True when user follows store"""
        user = User.objects.create(
            phone='+996555999999',
            full_name='Follower User',
            location='KG',
            is_active=True,
        )
        
        StoreFollower.objects.create(user=user, store=self.store)
        
        request = self.factory.get('/api/v1/stores/')
        request.user = user
        serializer = StoreListSerializer(instance=self.store, context={'request': request})
        data = serializer.data
        
        self.assertTrue(data['is_following'])
    
    def test_store_list_serializer_logo_url(self):
        """Test logo_url returns correct URL"""
        request = self.factory.get('/api/v1/stores/')
        from django.contrib.auth.models import AnonymousUser
        request.user = AnonymousUser()
        serializer = StoreListSerializer(instance=self.store, context={'request': request})
        data = serializer.data
        
        # logo_url should be in the response (can be None if no logo)
        self.assertIn('logo_url', data)
        self.assertIn('logo', data)


class StoreDetailSerializerTest(TestCase):
    """Test StoreDetailSerializer"""
    
    @classmethod
    def setUpTestData(cls):
        """Set up test data"""
        cls.owner = User.objects.create(
            phone='+996555123456',
            full_name='Store Owner',
            location='KG',
            is_active=True,
        )
        
        cls.store = Store.objects.create(
            name='Test Store',
            owner=cls.owner,
            market='KG',
            description='Test store description',
            email='store@example.com',
            phone='+996555123456',
            website='https://example.com',
            address='123 Test Street',
            status='active',
            is_active=True,
            is_verified=True,
            is_featured=True,
            rating=4.5,
            reviews_count=100,
            orders_count=500,
            products_count=50,
            likes_count=200,
        )
        
        cls.factory = APIRequestFactory()
    
    def test_store_detail_serializer_contains_expected_fields(self):
        """Test serializer contains all expected fields"""
        request = self.factory.get('/api/v1/stores/test-store/')
        from django.contrib.auth.models import AnonymousUser
        request.user = AnonymousUser()
        serializer = StoreDetailSerializer(instance=self.store, context={'request': request})
        data = serializer.data
        
        self.assertIn('id', data)
        self.assertIn('name', data)
        self.assertIn('slug', data)
        self.assertIn('description', data)
        self.assertIn('logo', data)
        self.assertIn('logo_url', data)
        self.assertIn('cover_image', data)
        self.assertIn('cover_image_url', data)
        self.assertIn('email', data)
        self.assertIn('phone', data)
        self.assertIn('website', data)
        self.assertIn('address', data)
        self.assertIn('rating', data)
        self.assertIn('reviews_count', data)
        self.assertIn('orders_count', data)
        self.assertIn('products_count', data)
        self.assertIn('likes_count', data)
        self.assertIn('is_verified', data)
        self.assertIn('is_featured', data)
        self.assertIn('status', data)
        self.assertIn('market', data)
        self.assertIn('owner', data)
        self.assertIn('owner_name', data)
        self.assertIn('is_following', data)
        self.assertIn('created_at', data)
        self.assertIn('updated_at', data)
    
    def test_store_detail_serializer_data_values(self):
        """Test serializer returns correct data values"""
        request = self.factory.get('/api/v1/stores/test-store/')
        from django.contrib.auth.models import AnonymousUser
        request.user = AnonymousUser()
        serializer = StoreDetailSerializer(instance=self.store, context={'request': request})
        data = serializer.data
        
        self.assertEqual(data['name'], 'Test Store')
        self.assertEqual(data['slug'], 'test-store')
        self.assertEqual(data['description'], 'Test store description')
        self.assertEqual(data['email'], 'store@example.com')
        self.assertEqual(data['phone'], '+996555123456')
        self.assertEqual(data['website'], 'https://example.com')
        self.assertEqual(data['address'], '123 Test Street')
        self.assertEqual(float(data['rating']), 4.5)
        self.assertEqual(data['status'], 'active')
        self.assertEqual(data['market'], 'KG')
        self.assertEqual(data['owner'], self.owner.id)
        self.assertEqual(data['owner_name'], 'Store Owner')
    
    def test_store_detail_serializer_owner_name(self):
        """Test owner_name returns owner's full_name"""
        request = self.factory.get('/api/v1/stores/test-store/')
        from django.contrib.auth.models import AnonymousUser
        request.user = AnonymousUser()
        serializer = StoreDetailSerializer(instance=self.store, context={'request': request})
        data = serializer.data
        
        self.assertEqual(data['owner_name'], self.owner.full_name)
    
    def test_store_detail_serializer_is_following(self):
        """Test is_following field"""
        user = User.objects.create(
            phone='+996555999999',
            full_name='Follower User',
            location='KG',
            is_active=True,
        )
        
        request = self.factory.get('/api/v1/stores/test-store/')
        request.user = user
        serializer = StoreDetailSerializer(instance=self.store, context={'request': request})
        data = serializer.data
        
        # User doesn't follow store yet
        self.assertFalse(data['is_following'])
        
        # User follows store
        StoreFollower.objects.create(user=user, store=self.store)
        serializer = StoreDetailSerializer(instance=self.store, context={'request': request})
        data = serializer.data
        self.assertTrue(data['is_following'])

