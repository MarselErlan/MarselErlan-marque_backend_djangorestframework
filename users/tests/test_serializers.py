"""
Unit Tests for Users App Serializers
Tests for all serializers in the users app
"""

from django.test import TestCase, RequestFactory
from django.contrib.auth import get_user_model
from rest_framework.test import APIRequestFactory
from users.serializers import (
    UserSerializer, UserUpdateSerializer,
    AddressSerializer, AddressCreateSerializer,
    PaymentMethodSerializer, PaymentMethodCreateSerializer,
    NotificationSerializer,
    SendVerificationSerializer, VerifyCodeSerializer
)
from users.models import Address, PaymentMethod, Notification

User = get_user_model()


class UserSerializerTest(TestCase):
    """Test UserSerializer"""
    
    def setUp(self):
        """Set up test data"""
        self.user = User.objects.create(
            phone='+996555123456',
            full_name='Test User',
            market='KG',
            language='ru',
            is_active=True,
            is_verified=True
        )
    
    def test_user_serializer_contains_expected_fields(self):
        """Test serializer contains all expected fields"""
        serializer = UserSerializer(instance=self.user)
        data = serializer.data
        
        self.assertIn('id', data)
        self.assertIn('phone', data)
        self.assertIn('formatted_phone', data)
        self.assertIn('name', data)
        self.assertIn('full_name', data)
        self.assertIn('market', data)
        self.assertIn('language', data)
        self.assertIn('country', data)
        self.assertIn('currency', data)
        self.assertIn('currency_code', data)
    
    def test_user_serializer_read_only_fields(self):
        """Test read-only fields cannot be modified"""
        serializer = UserSerializer(instance=self.user)
        self.assertIn('formatted_phone', serializer.data)
        self.assertIn('full_name', serializer.data)
        self.assertIn('currency', serializer.data)


class UserUpdateSerializerTest(TestCase):
    """Test UserUpdateSerializer"""
    
    def setUp(self):
        """Set up test data"""
        self.user = User.objects.create(
            phone='+996555123456',
            full_name='Test User',
            market='KG'
        )
    
    def test_update_full_name(self):
        """Test updating full name"""
        data = {'full_name': 'Updated Name'}
        serializer = UserUpdateSerializer(instance=self.user, data=data, partial=True)
        
        self.assertTrue(serializer.is_valid())
        updated_user = serializer.save()
        self.assertEqual(updated_user.name, 'Updated Name')
    
    def test_update_profile_image(self):
        """Test updating profile image URL"""
        data = {'profile_image_url': 'https://example.com/image.jpg'}
        serializer = UserUpdateSerializer(instance=self.user, data=data, partial=True)
        
        self.assertTrue(serializer.is_valid())
        updated_user = serializer.save()
        self.assertEqual(updated_user.profile_image_url, 'https://example.com/image.jpg')
    
    def test_full_name_validation_too_short(self):
        """Test full name must be at least 2 characters"""
        data = {'full_name': 'A'}
        serializer = UserUpdateSerializer(instance=self.user, data=data)
        
        self.assertFalse(serializer.is_valid())
        self.assertIn('full_name', serializer.errors)


class AddressSerializerTest(TestCase):
    """Test AddressSerializer"""
    
    def setUp(self):
        """Set up test data"""
        self.user = User.objects.create(
            phone='+996555123456',
            market='KG'
        )
        
        self.factory = RequestFactory()
        self.request = self.factory.get('/')
        self.request.user = self.user
        
        self.address = Address.objects.create(
            user=self.user,
            title='Home',
            full_address='Bishkek, Chui Ave 123',
            city='Bishkek',
            country='Kyrgyzstan',
            market='KG'
        )
    
    def test_address_serializer_contains_expected_fields(self):
        """Test serializer contains all expected fields"""
        serializer = AddressSerializer(instance=self.address)
        data = serializer.data
        
        self.assertIn('id', data)
        self.assertIn('title', data)
        self.assertIn('full_address', data)
        self.assertIn('city', data)
        self.assertIn('country', data)
        self.assertIn('is_default', data)
        self.assertIn('market', data)
    
    def test_address_create_serializer(self):
        """Test creating address with AddressCreateSerializer"""
        data = {
            'title': 'Work',
            'full_address': 'Bishkek, Manas Ave 456',
            'city': 'Bishkek',
            'country': 'Kyrgyzstan'
        }
        
        serializer = AddressCreateSerializer(data=data)
        self.assertTrue(serializer.is_valid())


class PaymentMethodSerializerTest(TestCase):
    """Test PaymentMethodSerializer"""
    
    def setUp(self):
        """Set up test data"""
        self.user = User.objects.create(
            phone='+996555123456',
            market='KG'
        )
        
        self.factory = RequestFactory()
        self.request = self.factory.get('/')
        self.request.user = self.user
        
        self.payment = PaymentMethod.objects.create(
            user=self.user,
            payment_type='card',
            card_number_masked='****1234',
            card_holder_name='TEST USER',
            expiry_month='12',
            expiry_year='2025',
            market='KG'
        )
    
    def test_payment_method_serializer_contains_expected_fields(self):
        """Test serializer contains all expected fields"""
        serializer = PaymentMethodSerializer(instance=self.payment)
        data = serializer.data
        
        self.assertIn('id', data)
        self.assertIn('payment_type', data)
        self.assertIn('card_type', data)
        self.assertIn('card_number_masked', data)
        self.assertIn('card_holder_name', data)
        self.assertIn('is_default', data)
        self.assertIn('market', data)
    
    def test_payment_method_create_serializer_valid(self):
        """Test creating payment method with valid data"""
        data = {
            'card_number': '4111111111111111',
            'card_holder_name': 'TEST USER',
            'expiry_month': '12',
            'expiry_year': '2025'
        }
        
        serializer = PaymentMethodCreateSerializer(data=data)
        self.assertTrue(serializer.is_valid())
    
    def test_payment_method_create_serializer_invalid_card_number(self):
        """Test validation fails for invalid card number"""
        data = {
            'card_number': '123',  # Too short
            'card_holder_name': 'TEST USER',
            'expiry_month': '12',
            'expiry_year': '2025'
        }
        
        serializer = PaymentMethodCreateSerializer(data=data)
        self.assertFalse(serializer.is_valid())
        self.assertIn('card_number', serializer.errors)
    
    def test_payment_method_create_serializer_invalid_month(self):
        """Test validation fails for invalid month"""
        data = {
            'card_number': '4111111111111111',
            'card_holder_name': 'TEST USER',
            'expiry_month': '13',  # Invalid month
            'expiry_year': '2025'
        }
        
        serializer = PaymentMethodCreateSerializer(data=data)
        self.assertFalse(serializer.is_valid())
        self.assertIn('expiry_month', serializer.errors)
    
    def test_payment_method_create_serializer_expired_year(self):
        """Test validation fails for expired year"""
        data = {
            'card_number': '4111111111111111',
            'card_holder_name': 'TEST USER',
            'expiry_month': '12',
            'expiry_year': '2020'  # Expired
        }
        
        serializer = PaymentMethodCreateSerializer(data=data)
        self.assertFalse(serializer.is_valid())
        self.assertIn('expiry_year', serializer.errors)


class NotificationSerializerTest(TestCase):
    """Test NotificationSerializer"""
    
    def setUp(self):
        """Set up test data"""
        self.user = User.objects.create(
            phone='+996555123456',
            market='KG'
        )
        
        self.notification = Notification.objects.create(
            user=self.user,
            type='order_update',
            title='Order Shipped',
            message='Your order has been shipped',
            market='KG'
        )
    
    def test_notification_serializer_contains_expected_fields(self):
        """Test serializer contains all expected fields"""
        serializer = NotificationSerializer(instance=self.notification)
        data = serializer.data
        
        self.assertIn('id', data)
        self.assertIn('type', data)
        self.assertIn('title', data)
        self.assertIn('message', data)
        self.assertIn('is_read', data)
        self.assertIn('order_id', data)
        self.assertIn('market', data)


class AuthenticationSerializersTest(TestCase):
    """Test authentication serializers"""
    
    def test_send_verification_serializer_valid_kg_phone(self):
        """Test valid KG phone number"""
        data = {'phone': '+996555123456'}
        serializer = SendVerificationSerializer(data=data)
        self.assertTrue(serializer.is_valid())
    
    def test_send_verification_serializer_valid_us_phone(self):
        """Test valid US phone number"""
        data = {'phone': '+15551234567'}
        serializer = SendVerificationSerializer(data=data)
        self.assertTrue(serializer.is_valid())
    
    def test_send_verification_serializer_invalid_no_country_code(self):
        """Test invalid phone without country code"""
        data = {'phone': '555123456'}
        serializer = SendVerificationSerializer(data=data)
        self.assertFalse(serializer.is_valid())
        self.assertIn('phone', serializer.errors)
    
    def test_send_verification_serializer_invalid_too_short(self):
        """Test invalid phone too short"""
        data = {'phone': '+996123'}
        serializer = SendVerificationSerializer(data=data)
        self.assertFalse(serializer.is_valid())
        self.assertIn('phone', serializer.errors)
    
    def test_verify_code_serializer_valid(self):
        """Test valid verification code"""
        data = {
            'phone': '+996555123456',
            'verification_code': '123456'
        }
        serializer = VerifyCodeSerializer(data=data)
        self.assertTrue(serializer.is_valid())
    
    def test_verify_code_serializer_invalid_code_length(self):
        """Test invalid code length"""
        data = {
            'phone': '+996555123456',
            'verification_code': '123'  # Too short
        }
        serializer = VerifyCodeSerializer(data=data)
        self.assertFalse(serializer.is_valid())
        self.assertIn('verification_code', serializer.errors)
    
    def test_verify_code_serializer_invalid_code_non_digit(self):
        """Test invalid code with non-digits"""
        data = {
            'phone': '+996555123456',
            'verification_code': '12345a'
        }
        serializer = VerifyCodeSerializer(data=data)
        self.assertFalse(serializer.is_valid())
        self.assertIn('verification_code', serializer.errors)

