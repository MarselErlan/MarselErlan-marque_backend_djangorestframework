"""
Tests for Referral Fee views.
Following TDD approach - tests first, then implementation.
"""

from django.test import TestCase
from decimal import Decimal
from rest_framework import status
from rest_framework.test import APIClient

from products.models import Category, Subcategory, Product, Brand, Currency
from stores.models import Store
from users.models import User
from referral_fee.models import ReferralFee


class ReferralFeeViewTests(TestCase):
    """Test Referral Fee API views."""
    
    @classmethod
    def setUpTestData(cls):
        """Set up test data"""
        # Create admin user
        cls.admin_user = User.objects.create_superuser(
            phone='+996555999999',
            password='admin123',
            location='KG',
        )
        
        # Create regular user
        cls.regular_user = User.objects.create(
            phone='+996555111111',
            full_name='Regular User',
            location='KG',
            is_active=True,
        )
        
        # Create categories
        cls.category = Category.objects.create(
            name='Electronics',
            slug='electronics',
            market='KG',
            is_active=True,
        )
        
        cls.subcategory1 = Subcategory.objects.create(
            category=cls.category,
            name='Smartphones',
            slug='smartphones',
            is_active=True,
        )
        
        cls.subcategory2 = Subcategory.objects.create(
            category=cls.category,
            parent_subcategory=cls.subcategory1,
            name='Android Phones',
            slug='android-phones',
            is_active=True,
        )
        
        # Create store and product
        cls.store_owner = User.objects.create(
            phone='+996555000006',
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
        
        cls.product = Product.objects.create(
            name='Test Product',
            slug='test-product',
            category=cls.category,
            subcategory=cls.subcategory1,
            second_subcategory=cls.subcategory2,
            store=cls.store,
            brand=cls.brand,
            currency=cls.currency,
            price=Decimal('1000.00'),
            market='KG',
            is_active=True,
            in_stock=True,
        )
        
        # Create referral fees
        cls.fee_category = ReferralFee.objects.create(
            category=cls.category,
            fee_percentage=Decimal('10.00'),
            fee_fixed=Decimal('0.00'),
            is_active=True,
        )
        
        cls.fee_full = ReferralFee.objects.create(
            category=cls.category,
            subcategory=cls.subcategory1,
            second_subcategory=cls.subcategory2,
            fee_percentage=Decimal('15.00'),
            fee_fixed=Decimal('50.00'),
            is_active=True,
        )
    
    def setUp(self):
        """Set up test client"""
        self.client = APIClient()
    
    def test_fee_list_requires_authentication(self):
        """Test that fee list requires authentication"""
        response = self.client.get('/api/v1/referral-fees/')
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
    
    def test_fee_list_success(self):
        """Test listing fees"""
        self.client.force_authenticate(user=self.regular_user)
        response = self.client.get('/api/v1/referral-fees/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['success'])
        self.assertIn('fees', response.data)
        self.assertEqual(len(response.data['fees']), 2)
    
    def test_fee_list_include_inactive(self):
        """Test listing fees including inactive"""
        # Create inactive fee
        ReferralFee.objects.create(
            category=self.category,
            fee_percentage=Decimal('5.00'),
            fee_fixed=Decimal('0.00'),
            is_active=False,
        )
        
        self.client.force_authenticate(user=self.regular_user)
        response = self.client.get('/api/v1/referral-fees/?include_inactive=true')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['fees']), 3)
    
    def test_fee_detail_success(self):
        """Test getting fee detail"""
        self.client.force_authenticate(user=self.regular_user)
        response = self.client.get(f'/api/v1/referral-fees/{self.fee_category.id}/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['success'])
        self.assertEqual(response.data['fee']['id'], self.fee_category.id)
    
    def test_fee_create_requires_admin(self):
        """Test that fee creation requires admin access"""
        self.client.force_authenticate(user=self.regular_user)
        response = self.client.post('/api/v1/referral-fees/create/', {
            'category': self.category.id,
            'fee_percentage': '12.00',
            'fee_fixed': '0.00',
            'is_active': True,
        })
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
    
    def test_fee_create_success(self):
        """Test creating a fee as admin"""
        self.client.force_authenticate(user=self.admin_user)
        response = self.client.post('/api/v1/referral-fees/create/', {
            'category': self.category.id,
            'fee_percentage': '12.00',
            'fee_fixed': '0.00',
            'is_active': True,
        })
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(response.data['success'])
        self.assertEqual(response.data['fee']['fee_percentage'], '12.00')
    
    def test_get_fee_for_product_success(self):
        """Test getting fee for a product"""
        self.client.force_authenticate(user=self.regular_user)
        response = self.client.get(f'/api/v1/referral-fees/product/{self.product.id}/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['success'])
        # Should return the most specific fee (fee_full)
        self.assertEqual(response.data['fee']['id'], self.fee_full.id)
    
    def test_calculate_fee_success(self):
        """Test calculating fee for a product"""
        self.client.force_authenticate(user=self.regular_user)
        response = self.client.post('/api/v1/referral-fees/calculate/', {
            'product_id': self.product.id,
            'order_amount': '1000.00',
        })
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['success'])
        # 15% of 1000 = 150, plus 50 fixed = 200
        self.assertEqual(response.data['fee_amount'], '200.00')
        self.assertEqual(response.data['order_amount'], '1000.00')

