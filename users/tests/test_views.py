"""
Integration Tests for Users App Views
Tests for all API endpoints: authentication, profile, addresses, payment methods, notifications
"""

from django.test import TestCase, override_settings
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from rest_framework import status
from rest_framework.authtoken.models import Token
from unittest.mock import patch
from django.core.files.uploadedfile import SimpleUploadedFile
from users.models import Address, PaymentMethod, Notification, UserPhoneNumber

User = get_user_model()


@override_settings(TESTING=True)
class AuthenticationAPITest(TestCase):
    """Integration tests for authentication endpoints"""
    
    def setUp(self):
        """Set up test client"""
        self.client = APIClient()
    
    @patch('users.views.TWILIO_READY', new=False)
    def test_send_verification_returns_503_when_twilio_unavailable(self):
        """Endpoint should surface service unavailable when Twilio is disabled"""
        from django.conf import settings
        self.assertTrue(settings.TESTING)
        response = self.client.post('/api/v1/auth/send-verification', {
            'phone': '+996555123456'
        }, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_503_SERVICE_UNAVAILABLE)
        self.assertFalse(response.data['success'])
        self.assertIn('detail', response.data)
    
    @patch('users.views.send_sms_via_twilio_verify')
    @patch('users.views.TWILIO_READY', new=True)
    def test_send_verification_success_with_twilio(self, mock_send_sms):
        """Twilio successfully sends a verification SMS"""
        mock_send_sms.return_value = True
        
        response = self.client.post('/api/v1/auth/send-verification', {
            'phone': '+15551234567'
        }, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['success'])
        self.assertEqual(response.data['location'], 'US')
        self.assertEqual(response.data['language'], 'en')
        self.assertNotIn('dev_code', response.data)
        mock_send_sms.assert_called_once_with('+15551234567')
    
    @patch('users.views.send_sms_via_twilio_verify')
    @patch('users.views.TWILIO_READY', new=True)
    def test_send_verification_twilio_failure_returns_502(self, mock_send_sms):
        """If Twilio cannot send the SMS, return 502"""
        mock_send_sms.return_value = False
        
        response = self.client.post('/api/v1/auth/send-verification', {
            'phone': '+996555123456'
        }, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_502_BAD_GATEWAY)
        self.assertFalse(response.data['success'])
        self.assertIn('detail', response.data)
    
    def test_send_verification_invalid_phone(self):
        """Test sending verification with invalid phone"""
        response = self.client.post('/api/v1/auth/send-verification', {
            'phone': '123'
        }, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
    
    @patch('users.views.TWILIO_READY', new=False)
    def test_verify_code_returns_503_when_twilio_unavailable(self):
        """Verification requires Twilio and should fail fast if disabled"""
        response = self.client.post('/api/v1/auth/verify-code', {
            'phone': '+996555123456',
            'verification_code': '123456'
        }, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_503_SERVICE_UNAVAILABLE)
        self.assertIn('detail', response.data)
    
    @patch('users.views.verify_code_via_twilio_verify')
    @patch('users.views.TWILIO_READY', new=True)
    def test_verify_code_success_with_twilio(self, mock_verify):
        """Successful verification through Twilio Verify"""
        mock_verify.return_value = True
        
        response = self.client.post('/api/v1/auth/verify-code', {
            'phone': '+996555123456',
            'verification_code': '123456'
        }, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('access_token', response.data)
        self.assertTrue(response.data['is_new_user'])
        mock_verify.assert_called_once_with('+996555123456', '123456')
        self.assertTrue(User.objects.filter(phone='+996555123456').exists())
    
    @patch('users.views.verify_code_via_twilio_verify')
    @patch('users.views.TWILIO_READY', new=True)
    def test_verify_code_invalid_with_twilio(self, mock_verify):
        """Invalid codes should return 400 when Twilio rejects them"""
        mock_verify.return_value = False
        
        response = self.client.post('/api/v1/auth/verify-code', {
            'phone': '+996555123456',
            'verification_code': '999999'
        }, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('detail', response.data)
    
    @patch('users.views.verify_code_via_twilio_verify')
    @patch('users.views.TWILIO_READY', new=True)
    def test_verify_code_us_number_sets_market(self, mock_verify):
        """US numbers should create users with US market metadata"""
        mock_verify.return_value = True
        
        response = self.client.post('/api/v1/auth/verify-code', {
            'phone': '+15551234567',
            'verification_code': '123456'
        }, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['location'], 'US')
        user = User.objects.get(phone='+15551234567')
        self.assertEqual(user.location, 'US')
        self.assertEqual(user.language, 'en')
    
    def test_logout_success(self):
        """Test successful logout"""
        user = User.objects.create(phone='+996555123456', location='KG')
        token = Token.objects.create(user=user)
        
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {token.key}')
        response = self.client.post('/api/v1/auth/logout')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['success'])
        
        # Verify token was deleted
        self.assertFalse(Token.objects.filter(key=token.key).exists())
    
    def test_logout_unauthorized(self):
        """Test logout without authentication"""
        response = self.client.post('/api/v1/auth/logout')
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


@override_settings(TESTING=True)
class ProfileAPITest(TestCase):
    """Integration tests for profile endpoints"""
    
    def setUp(self):
        """Set up test user and client"""
        self.user = User.objects.create(
            phone='+996555123456',
            full_name='Test User',
            location='KG',
            is_verified=True
        )
        self.token = Token.objects.create(user=self.user)
        self.client = APIClient()
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {self.token.key}')
    
    def test_get_profile_success(self):
        """Test getting user profile"""
        response = self.client.get('/api/v1/auth/profile')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['phone'], '+996555123456')
        self.assertEqual(response.data['location'], 'KG')
        self.assertIn('formatted_phone', response.data)
    
    def test_get_profile_unauthorized(self):
        """Test getting profile without authentication"""
        client = APIClient()
        response = client.get('/api/v1/auth/profile')
        
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
    
    def test_update_profile_success(self):
        """Test updating profile"""
        response = self.client.put('/api/v1/auth/profile', {
            'full_name': 'Updated Name',
        }, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['success'])
        
        # Verify updates
        self.user.refresh_from_db()
        self.assertEqual(self.user.name, 'Updated Name')
    
    def test_update_profile_image(self):
        """Test uploading profile image"""
        small_gif = (
            b'\x47\x49\x46\x38\x39\x61\x01\x00\x01\x00\x80\x00\x00\x00\x00\x00\xff\xff'
            b'\xff\x21\xf9\x04\x00\x00\x00\x00\x00\x2c\x00\x00\x00\x00\x01\x00\x01\x00'
            b'\x00\x02\x02\x4c\x01\x00\x3b'
        )
        image = SimpleUploadedFile("avatar.gif", small_gif, content_type="image/gif")
        response = self.client.put(
            '/api/v1/auth/profile',
            {'profile_image': image},
            format='multipart'
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['success'])

        self.user.refresh_from_db()
        self.assertTrue(bool(self.user.profile_image))
    
    def test_update_profile_invalid_data(self):
        """Test updating profile with invalid data"""
        response = self.client.put('/api/v1/auth/profile', {
            'full_name': 'A'  # Too short
        }, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


@override_settings(TESTING=True)
class AddressAPITest(TestCase):
    """Integration tests for address endpoints"""
    
    def setUp(self):
        """Set up test user and client"""
        self.user = User.objects.create(
            phone='+996555123456',
            location='KG'
        )
        self.token = Token.objects.create(user=self.user)
        self.client = APIClient()
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {self.token.key}')
        
        self.address = Address.objects.create(
            user=self.user,
            title='Home',
            full_address='Bishkek, Chui Ave 123',
            city='Bishkek',
            country='Kyrgyzstan',
            market='KG'
        )
    
    def test_list_addresses(self):
        """Test listing user addresses"""
        response = self.client.get('/api/v1/profile/addresses')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['success'])
        self.assertEqual(response.data['total'], 1)
        self.assertEqual(len(response.data['addresses']), 1)
    
    def test_create_address(self):
        """Test creating new address"""
        response = self.client.post('/api/v1/profile/addresses', {
            'title': 'Work',
            'full_address': 'Bishkek, Manas Ave 456',
            'city': 'Bishkek',
            'country': 'Kyrgyzstan'
        }, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(response.data['success'])
        
        # Verify address was created
        self.assertEqual(Address.objects.filter(user=self.user).count(), 2)
    
    def test_update_address(self):
        """Test updating address"""
        response = self.client.put(f'/api/v1/profile/addresses/{self.address.id}', {
            'title': 'Updated Home',
            'full_address': 'Bishkek, Updated Ave 789',
            'city': 'Bishkek'
        }, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['success'])
        
        # Verify updates
        self.address.refresh_from_db()
        self.assertEqual(self.address.title, 'Updated Home')

    def test_partial_update_address(self):
        """Test partial update via PATCH"""
        response = self.client.patch(
            f'/api/v1/profile/addresses/{self.address.id}',
            {
                'title': 'Patched Home',
                'is_default': True,
            },
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['success'])

        self.address.refresh_from_db()
        self.assertEqual(self.address.title, 'Patched Home')
        self.assertTrue(self.address.is_default)
    
    def test_delete_address(self):
        """Test deleting address"""
        response = self.client.delete(f'/api/v1/profile/addresses/{self.address.id}')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['success'])
        
        # Verify deletion
        self.assertFalse(Address.objects.filter(id=self.address.id).exists())
    
    def test_cannot_access_other_user_address(self):
        """Test user cannot access another user's addresses"""
        other_user = User.objects.create(phone='+996777888999', location='KG')
        other_address = Address.objects.create(
            user=other_user,
            title='Other Home',
            full_address='Other City',
            market='KG'
        )
        
        response = self.client.get(f'/api/v1/profile/addresses/{other_address.id}')
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)


@override_settings(TESTING=True)
class PhoneNumberAPITest(TestCase):
    """Integration tests for phone number endpoints"""
    
    def setUp(self):
        self.user = User.objects.create(
            phone='+996555123456',
            location='KG'
        )
        self.token = Token.objects.create(user=self.user)
        self.client = APIClient()
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {self.token.key}')
        
        self.phone_number = UserPhoneNumber.objects.create(
            user=self.user,
            phone='+996777888999',
            label='Home',
            is_primary=True
        )
    
    def test_list_phone_numbers(self):
        response = self.client.get('/api/v1/profile/phones')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['success'])
        self.assertEqual(response.data['total'], 1)
    
    def test_create_phone_number(self):
        response = self.client.post('/api/v1/profile/phones', {
            'label': 'Work',
            'phone': '+996700000001',
            'is_primary': False
        }, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(response.data['success'])
        self.assertEqual(UserPhoneNumber.objects.filter(user=self.user).count(), 2)
    
    def test_update_phone_number(self):
        response = self.client.patch(f'/api/v1/profile/phones/{self.phone_number.id}', {
            'label': 'Primary',
            'is_primary': True
        }, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['success'])
        self.phone_number.refresh_from_db()
        self.assertTrue(self.phone_number.is_primary)
    
    def test_delete_phone_number(self):
        response = self.client.delete(f'/api/v1/profile/phones/{self.phone_number.id}')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['success'])
        self.assertEqual(UserPhoneNumber.objects.filter(user=self.user).count(), 0)


@override_settings(TESTING=True)
class PaymentMethodAPITest(TestCase):
    """Integration tests for payment method endpoints"""
    
    def setUp(self):
        """Set up test user and client"""
        self.user = User.objects.create(
            phone='+996555123456',
            location='KG'
        )
        self.token = Token.objects.create(user=self.user)
        self.client = APIClient()
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {self.token.key}')
        
        self.payment = PaymentMethod.objects.create(
            user=self.user,
            card_number_masked='****1234',
            card_holder_name='TEST USER',
            expiry_month='12',
            expiry_year='2025',
            market='KG'
        )
    
    def test_list_payment_methods(self):
        """Test listing user payment methods"""
        response = self.client.get('/api/v1/profile/payment-methods')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['success'])
        self.assertEqual(response.data['total'], 1)
    
    def test_create_payment_method(self):
        """Test creating new payment method"""
        response = self.client.post('/api/v1/profile/payment-methods', {
            'card_number': '4111111111111111',
            'card_holder_name': 'TEST USER',
            'expiry_month': '12',
            'expiry_year': '2026'
        }, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(response.data['success'])
        
        # Verify payment method was created
        self.assertEqual(PaymentMethod.objects.filter(user=self.user).count(), 2)
    
    def test_update_payment_method_set_default(self):
        """Test updating payment method to set as default"""
        response = self.client.put(f'/api/v1/profile/payment-methods/{self.payment.id}', {
            'is_default': True
        }, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['success'])
        
        # Verify update
        self.payment.refresh_from_db()
        self.assertTrue(self.payment.is_default)
    
    def test_delete_payment_method(self):
        """Test deleting payment method"""
        response = self.client.delete(f'/api/v1/profile/payment-methods/{self.payment.id}')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['success'])
        
        # Verify deletion
        self.assertFalse(PaymentMethod.objects.filter(id=self.payment.id).exists())


@override_settings(TESTING=True)
class NotificationAPITest(TestCase):
    """Integration tests for notification endpoints"""
    
    def setUp(self):
        """Set up test user and client"""
        self.user = User.objects.create(
            phone='+996555123456',
            location='KG'
        )
        self.token = Token.objects.create(user=self.user)
        self.client = APIClient()
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {self.token.key}')
        
        # Create notifications
        self.notification1 = Notification.objects.create(
            user=self.user,
            type='order_update',
            title='Order Shipped',
            message='Your order has been shipped',
            market='KG'
        )
        
        self.notification2 = Notification.objects.create(
            user=self.user,
            type='promotion',
            title='New Sale',
            message='Check out our new sale',
            is_read=True,
            market='KG'
        )
    
    def test_list_all_notifications(self):
        """Test listing all notifications"""
        response = self.client.get('/api/v1/profile/notifications')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['success'])
        self.assertEqual(response.data['total'], 2)
        self.assertEqual(response.data['unread_count'], 1)
    
    def test_list_unread_notifications_only(self):
        """Test listing only unread notifications"""
        response = self.client.get('/api/v1/profile/notifications?unread_only=true')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['notifications']), 1)
        self.assertFalse(response.data['notifications'][0]['is_read'])
    
    def test_mark_notification_as_read(self):
        """Test marking single notification as read"""
        response = self.client.put(f'/api/v1/profile/notifications/{self.notification1.id}/read')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['success'])
        
        # Verify notification was marked as read
        self.notification1.refresh_from_db()
        self.assertTrue(self.notification1.is_read)
    
    def test_mark_all_notifications_as_read(self):
        """Test marking all notifications as read"""
        response = self.client.put('/api/v1/profile/notifications/read-all')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['success'])
        self.assertEqual(response.data['count'], 1)  # Only 1 was unread
        
        # Verify all notifications are marked as read
        unread_count = Notification.objects.filter(user=self.user, is_read=False).count()
        self.assertEqual(unread_count, 0)
    
    def test_pagination(self):
        """Test notification pagination"""
        # Create more notifications
        for i in range(25):
            Notification.objects.create(
                user=self.user,
                type='system',
                title=f'Notification {i}',
                message=f'Message {i}',
                market='KG'
            )
        
        # Test with limit
        response = self.client.get('/api/v1/profile/notifications?limit=10')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['notifications']), 10)
        self.assertGreater(response.data['total'], 10)

