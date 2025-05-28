# Security Test Suite

This directory contains comprehensive security tests for the image processing service API. The tests are designed to identify potential security vulnerabilities and ensure the application properly handles malicious inputs and unauthorized access attempts.

## Overview

The security test suite covers the following areas:

1. **JWT Token Security** - Authentication token validation and security
2. **Authentication Bypass** - Attempts to access protected resources without proper authentication
3. **Permission Testing** - User access controls and data isolation
4. **Input Validation** - Protection against injection attacks and malicious input
5. **File Upload Security** - File upload validation and security measures

## Test Structure

```
tests/security/
├── __init__.py              # Package initialization
├── base.py                  # Base test class with utilities
├── test_jwt_security.py     # JWT token security tests
├── test_auth_bypass.py      # Authentication bypass tests
├── test_permissions.py      # Permission and access control tests
├── test_input_validation.py # Input validation and sanitization tests
├── test_file_uploads.py     # File upload security tests
└── README.md               # This file
```

## Running the Tests

### Run All Security Tests
```bash
python manage.py test tests.security
```

### Run Individual Test Suites
```bash
# JWT Security Tests
python manage.py test tests.security.test_jwt_security

# Authentication Bypass Tests
python manage.py test tests.security.test_auth_bypass

# Permission Tests
python manage.py test tests.security.test_permissions

# Input Validation Tests
python manage.py test tests.security.test_input_validation

# File Upload Security Tests
python manage.py test tests.security.test_file_uploads
```

### Run Specific Test Classes
```bash
python manage.py test tests.security.test_jwt_security.JWTSecurityTest
python manage.py test tests.security.test_auth_bypass.AuthBypassTest
python manage.py test tests.security.test_permissions.PermissionTest
python manage.py test tests.security.test_input_validation.InputValidationTest
python manage.py test tests.security.test_file_uploads.FileUploadSecurityTest
```

### Run Individual Test Methods
```bash
python manage.py test tests.security.test_jwt_security.JWTSecurityTest.test_expired_token_rejected
python manage.py test tests.security.test_permissions.PermissionTest.test_user_cannot_access_other_users_image_detail
```

## Test Categories

### 1. JWT Security Tests (`test_jwt_security.py`)

Tests JWT token security including:

- **Token Expiration**: Ensures expired tokens are rejected
- **Signature Validation**: Tests tampered tokens are rejected
- **Algorithm Security**: Tests protection against algorithm manipulation (e.g., 'none' algorithm)
- **Refresh Token Security**: Tests refresh token validation and rotation
- **Malformed Tokens**: Tests handling of structurally invalid JWTs
- **Secret Key Validation**: Tests tokens signed with wrong keys are rejected

**Key Test Methods:**
- `test_expired_token_rejected()`
- `test_token_with_invalid_signature_rejected()`
- `test_none_algorithm_token_rejected()`
- `test_refresh_token_provides_new_access_token()`

### 2. Authentication Bypass Tests (`test_auth_bypass.py`)

Tests attempts to bypass authentication:

- **Unauthenticated Access**: Tests protected endpoints reject unauthenticated requests
- **Malformed Headers**: Tests invalid authorization headers are rejected
- **Token Format Attacks**: Tests various invalid token formats
- **SQL Injection in Headers**: Tests SQL injection attempts in auth headers
- **Unicode/Encoding Attacks**: Tests unicode and null byte injection

**Key Test Methods:**
- `test_protected_endpoints_without_auth_rejected()`
- `test_malformed_authorization_header_rejected()`
- `test_sql_injection_in_auth_header_handled()`
- `test_unicode_characters_in_auth_header_handled()`

### 3. Permission Tests (`test_permissions.py`)

Tests user access controls and data isolation:

- **Data Isolation**: Users can only access their own resources
- **Cross-User Access**: Tests users cannot access other users' data
- **Object-Level Permissions**: Tests detailed permission checking
- **Admin Permissions**: Tests admin user access patterns
- **Permission Bypassing**: Tests attempts to bypass object-level permissions

**Key Test Methods:**
- `test_user_can_only_see_own_images_in_list()`
- `test_user_cannot_access_other_users_image_detail()`
- `test_user_cannot_transform_other_users_image()`
- `test_cross_user_data_leakage_prevention()`

### 4. Input Validation Tests (`test_input_validation.py`)

Tests protection against injection attacks:

- **SQL Injection**: Tests SQL injection in various input fields
- **Cross-Site Scripting (XSS)**: Tests XSS payload handling
- **Path Traversal**: Tests directory traversal attempts
- **Command Injection**: Tests OS command injection attempts
- **JSON Injection**: Tests JSON structure manipulation
- **Integer Overflow**: Tests numeric overflow handling
- **Format String Attacks**: Tests format string vulnerabilities

**Key Test Methods:**
- `test_sql_injection_in_image_description()`
- `test_xss_in_image_metadata()`
- `test_path_traversal_in_filenames()`
- `test_command_injection_attempts()`

### 5. File Upload Security Tests (`test_file_uploads.py`)

Tests file upload security measures:

- **File Type Validation**: Tests non-image files are rejected
- **MIME Type Spoofing**: Tests protection against content-type lies
- **Malicious Filenames**: Tests dangerous filename handling
- **Executable Files**: Tests executable file detection
- **Polyglot Files**: Tests files valid in multiple formats
- **Size Limits**: Tests file size enforcement
- **Metadata Injection**: Tests malicious file metadata handling

**Key Test Methods:**
- `test_non_image_file_with_image_extension_rejected()`
- `test_malicious_filenames_sanitized()`
- `test_executable_file_upload_rejected()`
- `test_mime_type_spoofing()`

## Security Test Utilities

The `base.py` module provides common utilities for all security tests:

### Base Test Class: `SecurityTestBase`

Provides helper methods:
- `get_tokens_for_user(user)` - Generate JWT tokens
- `authenticate_user(user)` - Authenticate test client
- `create_test_image_file()` - Create valid test images
- `create_test_source_image()` - Create database image records
- `create_invalid_jwt_token()` - Create invalid tokens for testing
- `create_expired_jwt_token()` - Create expired tokens
- `create_malformed_file()` - Create malformed files for testing

### Test Users

Each test creates standard test users:
- `self.user_a` - Regular user for testing
- `self.user_b` - Second user for cross-user testing
- `self.admin_user` - Admin user for permission testing

## Expected Behaviors

### Security Test Assertions

The tests verify the following security behaviors:

1. **Authentication Required**: Protected endpoints return `401 Unauthorized` for unauthenticated requests
2. **Authorization Enforced**: Users cannot access other users' resources (return `404 Not Found` to avoid information leakage)
3. **Input Sanitization**: Malicious input is either rejected (`400 Bad Request`) or safely escaped
4. **File Validation**: Invalid files are rejected (`400 Bad Request`)
5. **Token Security**: Invalid, expired, or tampered tokens are rejected (`401 Unauthorized`)

### Error Handling

Security tests ensure that:
- No `500 Internal Server Error` responses occur due to malicious input
- Information leakage is minimized (e.g., `404` instead of `403` for unauthorized access)
- Error messages don't reveal sensitive system information

## Adding New Security Tests

When adding new security tests:

1. **Extend Base Class**: Inherit from `SecurityTestBase`
2. **Use Utilities**: Leverage existing helper methods
3. **Test Edge Cases**: Include boundary conditions and error cases
4. **Document Tests**: Add clear docstrings explaining what each test validates
5. **Update README**: Document new test categories or methods

### Example Test Structure

```python
def test_security_feature(self):
    """Test description of what security feature is being tested"""
    self.authenticate_user(self.user_a)
    
    # Arrange: Set up test data
    malicious_input = "'; DROP TABLE users; --"
    
    # Act: Perform the action being tested
    response = self.client.post('/api/endpoint/', {
        'field': malicious_input
    })
    
    # Assert: Verify security behavior
    self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
    # Additional assertions...
```

## Dependencies

The security tests require:

- Django Test Framework
- Django REST Framework Test Client
- PIL (Pillow) for image creation
- PyJWT for token manipulation
- unittest.mock for mocking external dependencies

## Continuous Integration

These security tests should be run:
- On every commit (CI/CD pipeline)
- Before deploying to production
- Regularly as part of security audits
- When adding new features or endpoints

## Security Notes

- Tests use mock S3 storage to avoid external dependencies
- Test images are created in-memory and not saved to disk
- Malicious payloads are safely contained within the test environment
- No actual security vulnerabilities are introduced by the test code 