"""
Tests for Store Admin API endpoints.
"""

from django.test import TestCase
from rest_framework import status
from rest_framework.test import APIClient
from decimal import Decimal

from users.models import User
from stores.models import Store
from products.models import Product, Category, Brand, Currency
from stores.permissions import IsStoreOwner


class StoreAdminAPITest(TestCase):
    """Test Store Admin API endpoints."""
    
    @classmethod
    def setUpTestData(cls):
        """Set up test data"""
        # Create store owner
        cls.store_owner = User.objects.create(
            phone='+996555111111',
            full_name='Store Owner',
            location='KG',
            is_active=True,
        )
        
        # Create another store owner
        cls.store_owner2 = User.objects.create(
            phone='+996555222222',
            full_name='Store Owner 2',
            location='KG',
            is_active=True,
        )
        
        # Create regular user (not a store owner)
        cls.regular_user = User.objects.create(
            phone='+996555333333',
            full_name='Regular User',
            location='KG',
            is_active=True,
        )
        
        # Create superuser
        cls.superuser = User.objects.create_superuser(
            phone='+996555999999',
            password='admin123',
            location='KG',
        )
        
        # Create stores
        cls.store1 = Store.objects.create(
            name='Store One',
            slug='store-one',
            owner=cls.store_owner,
            market='KG',
            status='active',
            is_active=True,
        )
        
        cls.store2 = Store.objects.create(
            name='Store Two',
            slug='store-two',
            owner=cls.store_owner2,
            market='KG',
            status='active',
            is_active=True,
        )
        
        # Create categories and brands
        cls.category = Category.objects.create(
            name='Electronics',
            slug='electronics',
            market='KG',
            is_active=True,
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
            store=cls.store1,
            brand=cls.brand,
            currency=cls.currency,
            price=Decimal('1000.00'),
            market='KG',
            is_active=True,
            in_stock=True,
        )
        
        cls.product2 = Product.objects.create(
            name='Product 2',
            slug='product-2',
            category=cls.category,
            store=cls.store2,
            brand=cls.brand,
            currency=cls.currency,
            price=Decimal('2000.00'),
            market='KG',
            is_active=True,
            in_stock=True,
        )
    
    def setUp(self):
        """Set up test client"""
        self.client = APIClient()
    
    def test_store_admin_product_list_requires_authentication(self):
        """Test that store admin endpoints require authentication"""
        response = self.client.get('/api/v1/stores/admin/products/')
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
    
    def test_store_admin_product_list_requires_store_owner(self):
        """Test that only store owners can access store admin"""
        self.client.force_authenticate(user=self.regular_user)
        response = self.client.get('/api/v1/stores/admin/products/')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
    
    def test_store_admin_product_list_success(self):
        """Test store owner can list their products"""
        self.client.force_authenticate(user=self.store_owner)
        response = self.client.get('/api/v1/stores/admin/products/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['success'])
        self.assertEqual(len(response.data['products']), 1)
        self.assertEqual(response.data['products'][0]['id'], self.product1.id)
    
    def test_store_admin_product_list_filter_by_store(self):
        """Test filtering products by store"""
        self.client.force_authenticate(user=self.store_owner)
        response = self.client.get(f'/api/v1/stores/admin/products/?store_id={self.store1.id}')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['products']), 1)
    
    def test_store_admin_product_detail_success(self):
        """Test store owner can view their product detail"""
        self.client.force_authenticate(user=self.store_owner)
        response = self.client.get(f'/api/v1/stores/admin/products/{self.product1.id}/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['success'])
        self.assertEqual(response.data['product']['id'], self.product1.id)
    
    def test_store_admin_product_detail_denies_other_store_products(self):
        """Test store owner cannot view other store's products"""
        self.client.force_authenticate(user=self.store_owner)
        response = self.client.get(f'/api/v1/stores/admin/products/{self.product2.id}/')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
    
    def test_store_admin_product_create_success(self):
        """Test store owner can create products"""
        self.client.force_authenticate(user=self.store_owner)
        response = self.client.post('/api/v1/stores/admin/products/create/', {
            'name': 'New Product',
            'slug': 'new-product',
            'category': self.category.id,
            'store': self.store1.id,
            'brand': self.brand.id,
            'currency': self.currency.id,
            'price': '1500.00',
            'market': 'KG',
            'is_active': True,
            'in_stock': True,
        })
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(response.data['success'])
    
    def test_store_admin_product_create_denies_wrong_store(self):
        """Test store owner cannot create products for other stores"""
        self.client.force_authenticate(user=self.store_owner)
        response = self.client.post('/api/v1/stores/admin/products/create/', {
            'name': 'New Product',
            'slug': 'new-product',
            'category': self.category.id,
            'store': self.store2.id,  # Wrong store
            'brand': self.brand.id,
            'currency': self.currency.id,
            'price': '1500.00',
            'market': 'KG',
            'is_active': True,
            'in_stock': True,
        })
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
    
    def test_store_admin_product_update_success(self):
        """Test store owner can update their products"""
        self.client.force_authenticate(user=self.store_owner)
        response = self.client.patch(f'/api/v1/stores/admin/products/{self.product1.id}/update/', {
            'name': 'Updated Product Name',
        })
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['success'])
        self.product1.refresh_from_db()
        self.assertEqual(self.product1.name, 'Updated Product Name')
    
    def test_store_admin_product_update_denies_store_change(self):
        """Test store owner cannot change product store"""
        self.client.force_authenticate(user=self.store_owner)
        response = self.client.patch(f'/api/v1/stores/admin/products/{self.product1.id}/update/', {
            'store': self.store2.id,
        })
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
    
    def test_store_admin_product_delete_success(self):
        """Test store owner can delete their products"""
        self.client.force_authenticate(user=self.store_owner)
        response = self.client.delete(f'/api/v1/stores/admin/products/{self.product1.id}/delete/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['success'])
        self.assertFalse(Product.objects.filter(id=self.product1.id).exists())
    
    def test_store_admin_product_delete_denies_other_store_products(self):
        """Test store owner cannot delete other store's products"""
        self.client.force_authenticate(user=self.store_owner)
        response = self.client.delete(f'/api/v1/stores/admin/products/{self.product2.id}/delete/')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
    
    def test_superuser_can_access_all_products(self):
        """Test superuser can access all products"""
        self.client.force_authenticate(user=self.superuser)
        # Superuser should be able to access even without owning stores
        response = self.client.get('/api/v1/stores/admin/products/')
        # Superuser should get 200 OK and see all products
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['success'])
        # Superuser should see all products from all stores
        self.assertGreaterEqual(len(response.data['products']), 2)
    
    def test_store_admin_my_stores(self):
        """Test store admin can get their stores list"""
        self.client.force_authenticate(user=self.store_owner)
        response = self.client.get('/api/v1/stores/admin/my-stores/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['success'])
        self.assertEqual(len(response.data['stores']), 1)
        self.assertEqual(response.data['stores'][0]['id'], self.store1.id)

