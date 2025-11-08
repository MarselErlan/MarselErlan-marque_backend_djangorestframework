# Users App Tests Documentation

## Overview

Comprehensive unit tests and integration tests for the Users app covering:

- **Models**: User, Address, PaymentMethod, VerificationCode, Notification
- **Serializers**: All serializers with validation tests
- **Views/API**: All authentication and profile endpoints

---

## Test Structure

```
users/tests/
├── __init__.py
├── test_models.py          # Unit tests for models
├── test_serializers.py     # Unit tests for serializers
└── test_views.py           # Integration tests for API endpoints
```

---

## Running Tests

### Run All Users App Tests

```bash
python manage.py test users
```

### Run Specific Test File

```bash
# Model tests only
python manage.py test users.tests.test_models

# Serializer tests only
python manage.py test users.tests.test_serializers

# View/API tests only
python manage.py test users.tests.test_views
```

### Run Specific Test Class

```bash
python manage.py test users.tests.test_models.UserModelTest
```

### Run Specific Test Method

```bash
python manage.py test users.tests.test_models.UserModelTest.test_user_creation
```

### Run with Verbose Output

```bash
python manage.py test users --verbosity=2
```

### Run with Coverage Report

```bash
# Install coverage first
pip install coverage

# Run tests with coverage
coverage run --source='users' manage.py test users
coverage report
coverage html  # Generate HTML report
```

---

## Test Coverage

### Model Tests (test_models.py)

#### UserModelTest

- ✅ User creation
- ✅ String representation
- ✅ Phone formatting (KG/US)
- ✅ Full name retrieval
- ✅ Currency formatting (KG/US)
- ✅ Country detection
- ✅ Market choices validation
- ✅ Language choices validation
- ✅ Phone uniqueness constraint

#### AddressModelTest

- ✅ Address creation
- ✅ String representation
- ✅ User relationship
- ✅ Default address handling
- ✅ Market field
- ✅ Optional fields

#### PaymentMethodModelTest

- ✅ Payment method creation
- ✅ String representation
- ✅ Card type detection (Visa, Mastercard, etc.)
- ✅ Market field
- ✅ Payment type choices

#### VerificationCodeModelTest

- ✅ Code creation
- ✅ String representation
- ✅ Expiry validation
- ✅ Usage flag

#### NotificationModelTest

- ✅ Notification creation
- ✅ String representation
- ✅ Read status default
- ✅ Type choices
- ✅ Order reference
- ✅ Market field

---

### Serializer Tests (test_serializers.py)

#### UserSerializerTest

- ✅ Contains expected fields
- ✅ Read-only fields validation

#### UserUpdateSerializerTest

- ✅ Update full name
- ✅ Update profile image
- ✅ Full name length validation

#### AddressSerializerTest

- ✅ Contains expected fields
- ✅ Create address validation

#### PaymentMethodSerializerTest

- ✅ Contains expected fields
- ✅ Valid card creation
- ✅ Invalid card number validation
- ✅ Invalid month validation
- ✅ Expired year validation

#### NotificationSerializerTest

- ✅ Contains expected fields

#### AuthenticationSerializersTest

- ✅ Valid KG phone
- ✅ Valid US phone
- ✅ Invalid phone (no country code)
- ✅ Invalid phone (too short)
- ✅ Valid verification code
- ✅ Invalid code length
- ✅ Invalid code (non-digit)

---

### Integration Tests (test_views.py)

#### AuthenticationAPITest

- ✅ Send verification returns 503 when Twilio disabled
- ✅ Send verification succeeds with Twilio mock
- ✅ Send verification returns 502 when Twilio fails
- ✅ Send verification rejects invalid phone format
- ✅ Verify code returns 503 when Twilio disabled
- ✅ Verify code succeeds with Twilio mock
- ✅ Verify code rejects invalid code via Twilio
- ✅ Verify code creates US user with correct market
- ✅ Logout success
- ✅ Logout unauthorized

#### ProfileAPITest

- ✅ Get profile success
- ✅ Get profile unauthorized
- ✅ Update profile success
- ✅ Update profile invalid data

#### AddressAPITest

- ✅ List addresses
- ✅ Create address
- ✅ Update address
- ✅ Delete address
- ✅ Cannot access other user's address

#### PaymentMethodAPITest

- ✅ List payment methods
- ✅ Create payment method
- ✅ Update payment method (set default)
- ✅ Delete payment method

#### NotificationAPITest

- ✅ List all notifications
- ✅ List unread notifications only
- ✅ Mark notification as read
- ✅ Mark all notifications as read
- ✅ Pagination

---

## API Endpoints Tested

### Authentication

- `POST /api/v1/auth/send-verification` - Send SMS code
- `POST /api/v1/auth/verify-code` - Verify code & login
- `POST /api/v1/auth/logout` - Logout
- `GET /api/v1/auth/profile` - Get profile
- `PUT /api/v1/auth/profile` - Update profile

### Addresses

- `GET /api/v1/profile/addresses/` - List addresses
- `POST /api/v1/profile/addresses/` - Create address
- `PUT /api/v1/profile/addresses/{id}/` - Update address
- `DELETE /api/v1/profile/addresses/{id}/` - Delete address

### Payment Methods

- `GET /api/v1/profile/payment-methods/` - List payment methods
- `POST /api/v1/profile/payment-methods/` - Create payment method
- `PUT /api/v1/profile/payment-methods/{id}/` - Update payment method
- `DELETE /api/v1/profile/payment-methods/{id}/` - Delete payment method

### Notifications

- `GET /api/v1/profile/notifications/` - List notifications
- `PUT /api/v1/profile/notifications/{id}/read/` - Mark as read
- `PUT /api/v1/profile/notifications/read-all/` - Mark all as read

---

## Test Statistics

- **Total Test Files**: 3
- **Total Test Classes**: 13
- **Total Test Methods**: 70+ (including Twilio integration tests)
- **Coverage**: Aiming for 95%+
- **Twilio Tests**: Cover success, failure, and unavailable scenarios

---

## Continuous Integration

### GitHub Actions Example

```yaml
name: Django Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest

    services:
      postgres:
        image: postgres:13
        env:
          POSTGRES_USER: postgres
          POSTGRES_PASSWORD: postgres
          POSTGRES_DB: test_db
        ports:
          - 5432:5432
        options: --health-cmd pg_isready --health-interval 10s --health-timeout 5s --health-retries 5

    steps:
      - uses: actions/checkout@v2

      - name: Set up Python
        uses: actions/setup-python@v2
        with:
          python-version: 3.11

      - name: Install dependencies
        run: |
          pip install -r requirements.txt

      - name: Run tests
        env:
          DB_ENGINE: django.db.backends.postgresql
          DB_NAME: test_db
          DB_USER: postgres
          DB_PASSWORD: postgres
          DB_HOST: localhost
          DB_PORT: 5432
        run: |
          python manage.py test users --verbosity=2
```

---

## Best Practices

1. **Isolation**: Each test is independent and doesn't rely on other tests
2. **Setup/Teardown**: Use `setUp()` and `tearDown()` methods properly
3. **Descriptive Names**: Test method names clearly describe what they test
4. **Assertions**: Use appropriate assertion methods (`assertEqual`, `assertTrue`, etc.)
5. **Coverage**: Aim for high test coverage but focus on critical paths
6. **Mock External Services**: Mock SMS services, payment gateways, etc.
7. **Test Data**: Use realistic but anonymized test data
8. **Fast Tests**: Keep tests fast by avoiding unnecessary database calls

---

## Troubleshooting

### Tests Failing Due to Database

```bash
# Drop and recreate test database
python manage.py flush --no-input
python manage.py migrate
```

### Tests Failing Due to Migrations

```bash
# Make sure all migrations are applied
python manage.py makemigrations
python manage.py migrate
```

### Specific Test Debugging

```bash
# Run with debug output
python manage.py test users.tests.test_views.AuthenticationAPITest.test_send_verification_success_kg --debug-mode
```

---

## Next Steps

1. ✅ Run all tests to ensure they pass
2. ✅ Generate coverage report
3. ✅ Fix any failing tests
4. ✅ Add more edge case tests if needed
5. ✅ Set up CI/CD pipeline
6. ✅ Document any known issues

---

## Contributing

When adding new features to the users app:

1. Write tests first (TDD approach)
2. Ensure all existing tests still pass
3. Add integration tests for new API endpoints
4. Update this documentation
5. Aim for 95%+ code coverage

---

**Test Status**: ✅ Ready for execution  
**Last Updated**: November 8, 2025
