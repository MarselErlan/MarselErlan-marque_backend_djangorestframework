"""
Tests for making store field required in Product model.
Following TDD approach.
"""

from django.test import TestCase
from django.core.exceptions import ValidationError
from products.models import Product, Category, Brand, Currency
from stores.models import Store
from users.models import User


class ProductStoreRequiredTest(TestCase):
    """Test that Product requires a store."""
    
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
            status='active',
            is_active=True,
        )
        
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
        
        cls.currency = Currency.objects.create(
            code='KGS',
            name='Kyrgyzstani Som',
            symbol='сом',
            exchange_rate=1.0,
            is_base=True,
            market='KG',
        )
    
    def test_product_requires_store(self):
        """Test that Product cannot be created without a store"""
        # Try to create product without store - should fail
        with self.assertRaises(Exception):  # Should raise ValidationError or IntegrityError
            product = Product(
                name='Product Without Store',
                slug='product-without-store',
                category=self.category,
                brand=self.brand,
                market='KG',
                price=1000.00,
                currency=self.currency,
                is_active=True,
                in_stock=True,
                # store is missing - should cause error
            )
            product.full_clean()  # This should raise ValidationError if model validation exists
            product.save()  # This should raise IntegrityError from database constraint
    
    def test_product_with_store_succeeds(self):
        """Test that Product can be created with a store"""
        product = Product.objects.create(
            name='Product With Store',
            slug='product-with-store',
            category=self.category,
            brand=self.brand,
            store=self.store,
            market='KG',
            price=1000.00,
            currency=self.currency,
            is_active=True,
            in_stock=True,
        )
        
        self.assertIsNotNone(product.id)
        self.assertEqual(product.store, self.store)
        self.assertIsNotNone(product.store)
    
    def test_product_store_cascade_delete(self):
        """Test that deleting a store deletes its products"""
        product = Product.objects.create(
            name='Product To Delete',
            slug='product-to-delete',
            category=self.category,
            brand=self.brand,
            store=self.store,
            market='KG',
            price=1000.00,
            currency=self.currency,
            is_active=True,
            in_stock=True,
        )
        
        product_id = product.id
        self.store.delete()
        
        # Product should be deleted due to CASCADE
        self.assertFalse(Product.objects.filter(id=product_id).exists())

