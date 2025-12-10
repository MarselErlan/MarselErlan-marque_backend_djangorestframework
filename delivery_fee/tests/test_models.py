"""
Tests for DeliveryFee models.
Following TDD approach - tests first, then implementation.
"""

from django.test import TestCase
from django.core.exceptions import ValidationError
from decimal import Decimal
from products.models import Category, Subcategory
from delivery_fee.models import DeliveryFee


class DeliveryFeeModelTest(TestCase):
    """Test DeliveryFee model."""
    
    @classmethod
    def setUpTestData(cls):
        """Set up test data"""
        # Create categories
        cls.category = Category.objects.create(
            name='Electronics',
            slug='electronics',
            market='KG',
            is_active=True,
        )
        
        cls.category2 = Category.objects.create(
            name='Clothing',
            slug='clothing',
            market='KG',
            is_active=True,
        )
        
        # Create first-level subcategory
        cls.subcategory1 = Subcategory.objects.create(
            category=cls.category,
            name='Smartphones',
            slug='smartphones',
            is_active=True,
        )
        
        # Create second-level subcategory (has parent_subcategory)
        cls.subcategory2 = Subcategory.objects.create(
            category=cls.category,
            parent_subcategory=cls.subcategory1,
            name='Android Phones',
            slug='android-phones',
            is_active=True,
        )
        
        # Create another first-level subcategory
        cls.subcategory3 = Subcategory.objects.create(
            category=cls.category2,
            name='T-Shirts',
            slug='t-shirts',
            is_active=True,
        )
    
    def test_delivery_fee_creation_with_category_only(self):
        """Test creating a delivery fee with only category"""
        fee = DeliveryFee.objects.create(
            category=self.category,
            fee_amount=Decimal('100.00'),
            is_active=True,
        )
        
        self.assertEqual(fee.category, self.category)
        self.assertIsNone(fee.subcategory)
        self.assertIsNone(fee.second_subcategory)
        self.assertEqual(fee.fee_amount, Decimal('100.00'))
        self.assertTrue(fee.is_active)
    
    def test_delivery_fee_creation_with_category_and_subcategory(self):
        """Test creating a delivery fee with category and first-level subcategory"""
        fee = DeliveryFee.objects.create(
            category=self.category,
            subcategory=self.subcategory1,
            fee_amount=Decimal('150.00'),
            is_active=True,
        )
        
        self.assertEqual(fee.category, self.category)
        self.assertEqual(fee.subcategory, self.subcategory1)
        self.assertIsNone(fee.second_subcategory)
        self.assertEqual(fee.fee_amount, Decimal('150.00'))
    
    def test_delivery_fee_creation_with_all_levels(self):
        """Test creating a delivery fee with category, subcategory, and second_subcategory"""
        fee = DeliveryFee.objects.create(
            category=self.category,
            subcategory=self.subcategory1,
            second_subcategory=self.subcategory2,
            fee_amount=Decimal('200.00'),
            is_active=True,
        )
        
        self.assertEqual(fee.category, self.category)
        self.assertEqual(fee.subcategory, self.subcategory1)
        self.assertEqual(fee.second_subcategory, self.subcategory2)
        self.assertEqual(fee.fee_amount, Decimal('200.00'))
    
    def test_delivery_fee_requires_category(self):
        """Test that category is required"""
        with self.assertRaises(ValidationError):
            fee = DeliveryFee(
                fee_amount=Decimal('100.00'),
                is_active=True,
            )
            fee.full_clean()
            fee.save()
    
    def test_delivery_fee_cannot_have_second_subcategory_without_subcategory(self):
        """Test that second_subcategory requires subcategory"""
        with self.assertRaises(ValidationError):
            fee = DeliveryFee(
                category=self.category,
                second_subcategory=self.subcategory2,
                fee_amount=Decimal('100.00'),
                is_active=True,
            )
            fee.full_clean()
    
    def test_delivery_fee_second_subcategory_must_be_child_of_subcategory(self):
        """Test that second_subcategory must be a child of subcategory"""
        # subcategory2 is a child of subcategory1, so this should work
        fee = DeliveryFee.objects.create(
            category=self.category,
            subcategory=self.subcategory1,
            second_subcategory=self.subcategory2,
            fee_amount=Decimal('200.00'),
            is_active=True,
        )
        self.assertIsNotNone(fee)
        
        # subcategory3 is not a child of subcategory1, so this should fail
        with self.assertRaises(ValidationError):
            fee = DeliveryFee(
                category=self.category,
                subcategory=self.subcategory1,
                second_subcategory=self.subcategory3,  # Wrong parent
                fee_amount=Decimal('200.00'),
                is_active=True,
            )
            fee.full_clean()
    
    def test_delivery_fee_fee_amount_validation(self):
        """Test fee_amount validation (non-negative)"""
        # Valid amount
        fee = DeliveryFee.objects.create(
            category=self.category,
            fee_amount=Decimal('100.00'),
            is_active=True,
        )
        self.assertEqual(fee.fee_amount, Decimal('100.00'))
        
        # Invalid: negative
        with self.assertRaises(ValidationError):
            fee = DeliveryFee(
                category=self.category,
                fee_amount=Decimal('-50.00'),
                is_active=True,
            )
            fee.full_clean()
    
    def test_delivery_fee_get_fee_for_product(self):
        """Test getting fee for a product based on its category structure"""
        from products.models import Product, Brand, Currency
        from stores.models import Store
        from users.models import User
        
        # Create fee for category only
        category_fee = DeliveryFee.objects.create(
            category=self.category,
            fee_amount=Decimal('100.00'),
            is_active=True,
        )
        
        # Create fee for category + subcategory
        subcategory_fee = DeliveryFee.objects.create(
            category=self.category,
            subcategory=self.subcategory1,
            fee_amount=Decimal('150.00'),
            is_active=True,
        )
        
        # Create fee for all levels
        full_fee = DeliveryFee.objects.create(
            category=self.category,
            subcategory=self.subcategory1,
            second_subcategory=self.subcategory2,
            fee_amount=Decimal('200.00'),
            is_active=True,
        )
        
        # Create test data for products
        store_owner = User.objects.create(
            phone='+996555000008',
            full_name='Store Owner',
            location='KG',
            is_active=True,
        )
        
        store = Store.objects.create(
            name='Test Store',
            owner=store_owner,
            market='KG',
            status='active',
            is_active=True,
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
        
        # Test: Product with only category should get category_fee
        product_category_only = Product.objects.create(
            name='Product Category Only',
            slug='product-category-only',
            category=self.category,
            store=store,
            brand=brand,
            currency=currency,
            price=Decimal('1000.00'),
            market='KG',
            is_active=True,
            in_stock=True,
        )
        
        fee = DeliveryFee.get_fee_for_product(product_category_only)
        self.assertEqual(fee, category_fee)
        
        # Test: Product with category + subcategory should get subcategory_fee
        product_with_subcategory = Product.objects.create(
            name='Product With Subcategory',
            slug='product-with-subcategory',
            category=self.category,
            subcategory=self.subcategory1,
            store=store,
            brand=brand,
            currency=currency,
            price=Decimal('1000.00'),
            market='KG',
            is_active=True,
            in_stock=True,
        )
        
        fee = DeliveryFee.get_fee_for_product(product_with_subcategory)
        self.assertEqual(fee, subcategory_fee)
        
        # Test: Product with all levels should get full_fee (most specific)
        product_full = Product.objects.create(
            name='Product Full',
            slug='product-full',
            category=self.category,
            subcategory=self.subcategory1,
            second_subcategory=self.subcategory2,
            store=store,
            brand=brand,
            currency=currency,
            price=Decimal('1000.00'),
            market='KG',
            is_active=True,
            in_stock=True,
        )
        
        fee = DeliveryFee.get_fee_for_product(product_full)
        self.assertEqual(fee, full_fee)
    
    def test_delivery_fee_most_specific_takes_precedence(self):
        """Test that more specific fees (with more levels) take precedence"""
        from products.models import Product, Brand, Currency
        from stores.models import Store
        from users.models import User
        
        # Create fees at different levels
        category_fee = DeliveryFee.objects.create(
            category=self.category,
            fee_amount=Decimal('100.00'),
            is_active=True,
        )
        
        subcategory_fee = DeliveryFee.objects.create(
            category=self.category,
            subcategory=self.subcategory1,
            fee_amount=Decimal('150.00'),
            is_active=True,
        )
        
        full_fee = DeliveryFee.objects.create(
            category=self.category,
            subcategory=self.subcategory1,
            second_subcategory=self.subcategory2,
            fee_amount=Decimal('200.00'),
            is_active=True,
        )
        
        # Create test data
        store_owner = User.objects.create(
            phone='+996555000009',
            full_name='Store Owner',
            location='KG',
            is_active=True,
        )
        
        store = Store.objects.create(
            name='Test Store',
            owner=store_owner,
            market='KG',
            status='active',
            is_active=True,
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
        
        # For a product with category, subcategory, and second_subcategory,
        # the most specific fee (full_fee) should be used
        product = Product.objects.create(
            name='Product Full',
            slug='product-full-prec',
            category=self.category,
            subcategory=self.subcategory1,
            second_subcategory=self.subcategory2,
            store=store,
            brand=brand,
            currency=currency,
            price=Decimal('1000.00'),
            market='KG',
            is_active=True,
            in_stock=True,
        )
        
        fee = DeliveryFee.get_fee_for_product(product)
        self.assertEqual(fee, full_fee)  # Most specific should win
        self.assertNotEqual(fee, subcategory_fee)
        self.assertNotEqual(fee, category_fee)

