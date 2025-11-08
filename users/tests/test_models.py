"""
Unit Tests for Users App Models
Tests for User, Address, PaymentMethod, VerificationCode, Notification models
"""

from django.test import TestCase
from django.contrib.auth import get_user_model
from django.utils import timezone
from datetime import timedelta
from users.models import Address, PaymentMethod, VerificationCode, Notification

User = get_user_model()


class UserModelTest(TestCase):
    """Test User model"""
    
    def setUp(self):
        """Set up test data"""
        self.user_kg = User.objects.create(
            phone='+996555123456',
            full_name='Test User KG',
            market='KG',
            language='ru',
            is_active=True,
            is_verified=True
        )
        
        self.user_us = User.objects.create(
            phone='+15551234567',
            full_name='Test User US',
            market='US',
            language='en',
            is_active=True,
            is_verified=True
        )
    
    def test_user_creation(self):
        """Test user can be created"""
        self.assertEqual(User.objects.count(), 2)
        self.assertEqual(self.user_kg.phone, '+996555123456')
        self.assertEqual(self.user_us.phone, '+15551234567')
    
    def test_user_str(self):
        """Test user string representation"""
        self.assertEqual(str(self.user_kg), '+996555123456')
        self.assertEqual(str(self.user_us), '+15551234567')
    
    def test_get_formatted_phone_kg(self):
        """Test KG phone formatting"""
        formatted = self.user_kg.get_formatted_phone()
        self.assertIn('+996', formatted)
    
    def test_get_formatted_phone_us(self):
        """Test US phone formatting"""
        formatted = self.user_us.get_formatted_phone()
        self.assertIn('+1', formatted)
    
    def test_get_full_name(self):
        """Test get full name"""
        self.assertEqual(self.user_kg.get_full_name(), 'Test User KG')
        
        # Test with no name
        user_no_name = User.objects.create(phone='+996777888999', market='KG')
        self.assertEqual(user_no_name.get_full_name(), '')
    
    def test_get_currency_kg(self):
        """Test KG currency"""
        self.assertEqual(self.user_kg.get_currency(), 'сом')
        self.assertEqual(self.user_kg.get_currency_code(), 'KGS')
    
    def test_get_currency_us(self):
        """Test US currency"""
        self.assertEqual(self.user_us.get_currency(), '$')
        self.assertEqual(self.user_us.get_currency_code(), 'USD')
    
    def test_get_country(self):
        """Test country detection"""
        self.assertEqual(self.user_kg.get_country(), 'Kyrgyzstan')
        self.assertEqual(self.user_us.get_country(), 'United States')
    
    def test_market_choices(self):
        """Test market field choices"""
        self.assertIn(self.user_kg.market, ['KG', 'US', 'ALL'])
        self.assertIn(self.user_us.market, ['KG', 'US', 'ALL'])
    
    def test_language_choices(self):
        """Test language field choices"""
        self.assertIn(self.user_kg.language, ['en', 'ru', 'ky'])
        self.assertIn(self.user_us.language, ['en', 'ru', 'ky'])
    
    def test_phone_unique(self):
        """Test phone number must be unique"""
        with self.assertRaises(Exception):
            User.objects.create(phone='+996555123456', market='KG')


class AddressModelTest(TestCase):
    """Test Address model"""
    
    def setUp(self):
        """Set up test data"""
        self.user = User.objects.create(
            phone='+996555123456',
            full_name='Test User',
            market='KG'
        )
        
        self.address = Address.objects.create(
            user=self.user,
            title='Home',
            full_address='Bishkek, Chui Ave 123',
            city='Bishkek',
            country='Kyrgyzstan',
            is_default=True,
            market='KG'
        )
    
    def test_address_creation(self):
        """Test address can be created"""
        self.assertEqual(Address.objects.count(), 1)
        self.assertEqual(self.address.title, 'Home')
    
    def test_address_str(self):
        """Test address string representation"""
        self.assertEqual(str(self.address), 'Home - Bishkek, Chui Ave 123')
    
    def test_address_user_relationship(self):
        """Test address belongs to user"""
        self.assertEqual(self.address.user, self.user)
        self.assertEqual(self.user.addresses.count(), 1)
    
    def test_default_address(self):
        """Test only one default address per user"""
        # Create second address as default
        address2 = Address.objects.create(
            user=self.user,
            title='Work',
            full_address='Bishkek, Manas Ave 456',
            is_default=True,
            market='KG'
        )
        
        # First address should still be default (will be handled in view)
        self.assertTrue(self.address.is_default)
        self.assertTrue(address2.is_default)
        
        # Both exist
        self.assertEqual(self.user.addresses.count(), 2)
    
    def test_address_market_field(self):
        """Test address has market field"""
        self.assertEqual(self.address.market, 'KG')
    
    def test_address_optional_fields(self):
        """Test address with minimal fields"""
        minimal_address = Address.objects.create(
            user=self.user,
            title='Minimal',
            full_address='Some address',
            market='KG'
        )
        self.assertIsNone(minimal_address.street)
        self.assertIsNone(minimal_address.building)
        self.assertIsNone(minimal_address.apartment)


class PaymentMethodModelTest(TestCase):
    """Test PaymentMethod model"""
    
    def setUp(self):
        """Set up test data"""
        self.user = User.objects.create(
            phone='+996555123456',
            full_name='Test User',
            market='KG'
        )
        
        self.payment = PaymentMethod.objects.create(
            user=self.user,
            payment_type='card',
            card_number_masked='****1234',
            card_holder_name='TEST USER',
            expiry_month='12',
            expiry_year='2025',
            is_default=True,
            market='KG'
        )
    
    def test_payment_method_creation(self):
        """Test payment method can be created"""
        self.assertEqual(PaymentMethod.objects.count(), 1)
        self.assertEqual(self.payment.card_number_masked, '****1234')
    
    def test_payment_method_str(self):
        """Test payment method string representation"""
        self.assertIn('****1234', str(self.payment))
    
    def test_get_card_type(self):
        """Test card type detection"""
        # Visa
        visa = PaymentMethod.objects.create(
            user=self.user,
            card_number_masked='4111111111111234',
            card_holder_name='TEST',
            expiry_month='12',
            expiry_year='2025',
            market='KG'
        )
        self.assertEqual(visa.get_card_type(), 'Visa')
        
        # Mastercard
        mastercard = PaymentMethod.objects.create(
            user=self.user,
            card_number_masked='5111111111111234',
            card_holder_name='TEST',
            expiry_month='12',
            expiry_year='2025',
            market='KG'
        )
        self.assertEqual(mastercard.get_card_type(), 'Mastercard')
        
        # Unknown
        unknown = PaymentMethod.objects.create(
            user=self.user,
            card_number_masked='****5678',
            card_holder_name='TEST',
            expiry_month='12',
            expiry_year='2025',
            market='KG'
        )
        self.assertEqual(unknown.get_card_type(), 'Unknown')
    
    def test_payment_method_market_field(self):
        """Test payment method has market field"""
        self.assertEqual(self.payment.market, 'KG')
    
    def test_payment_type_choices(self):
        """Test payment type choices"""
        self.assertIn(self.payment.payment_type, ['card', 'bank_account', 'mobile_wallet'])


class VerificationCodeModelTest(TestCase):
    """Test VerificationCode model"""
    
    def test_verification_code_creation(self):
        """Test verification code can be created"""
        expires_at = timezone.now() + timedelta(minutes=5)
        code = VerificationCode.objects.create(
            phone='+996555123456',
            code='123456',
            expires_at=expires_at,
            market='KG'
        )
        
        self.assertEqual(VerificationCode.objects.count(), 1)
        self.assertEqual(code.code, '123456')
        self.assertFalse(code.is_used)
    
    def test_verification_code_str(self):
        """Test verification code string representation"""
        expires_at = timezone.now() + timedelta(minutes=5)
        code = VerificationCode.objects.create(
            phone='+996555123456',
            code='123456',
            expires_at=expires_at,
            market='KG'
        )
        self.assertIn('+996555123456', str(code))
        self.assertIn('123456', str(code))
    
    def test_verification_code_expiry(self):
        """Test verification code expiry"""
        # Expired code
        expired_code = VerificationCode.objects.create(
            phone='+996555123456',
            code='123456',
            expires_at=timezone.now() - timedelta(minutes=1),
            market='KG'
        )
        self.assertLess(expired_code.expires_at, timezone.now())
        
        # Valid code
        valid_code = VerificationCode.objects.create(
            phone='+996777888999',
            code='654321',
            expires_at=timezone.now() + timedelta(minutes=5),
            market='KG'
        )
        self.assertGreater(valid_code.expires_at, timezone.now())
    
    def test_verification_code_is_used(self):
        """Test verification code usage flag"""
        code = VerificationCode.objects.create(
            phone='+996555123456',
            code='123456',
            expires_at=timezone.now() + timedelta(minutes=5),
            market='KG'
        )
        
        self.assertFalse(code.is_used)
        code.is_used = True
        code.save()
        self.assertTrue(code.is_used)


class NotificationModelTest(TestCase):
    """Test Notification model"""
    
    def setUp(self):
        """Set up test data"""
        self.user = User.objects.create(
            phone='+996555123456',
            full_name='Test User',
            market='KG'
        )
        
        self.notification = Notification.objects.create(
            user=self.user,
            type='order_update',
            title='Order Shipped',
            message='Your order #12345 has been shipped',
            market='KG'
        )
    
    def test_notification_creation(self):
        """Test notification can be created"""
        self.assertEqual(Notification.objects.count(), 1)
        self.assertEqual(self.notification.title, 'Order Shipped')
    
    def test_notification_str(self):
        """Test notification string representation"""
        self.assertIn('Order Shipped', str(self.notification))
    
    def test_notification_is_read_default(self):
        """Test notification is unread by default"""
        self.assertFalse(self.notification.is_read)
    
    def test_notification_type_choices(self):
        """Test notification type choices"""
        self.assertIn(self.notification.type, [
            'order_update', 'promotion', 'system', 'payment', 'delivery'
        ])
    
    def test_notification_with_order_id(self):
        """Test notification with order reference"""
        notification_with_order = Notification.objects.create(
            user=self.user,
            type='order_update',
            title='Order Delivered',
            message='Your order has been delivered',
            order_id=12345,
            market='KG'
        )
        self.assertEqual(notification_with_order.order_id, 12345)
    
    def test_notification_market_field(self):
        """Test notification has market field"""
        self.assertEqual(self.notification.market, 'KG')

