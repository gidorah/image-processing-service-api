"""
Security Test Runner

This module provides a convenient way to run all security tests for the image processing service.
It includes tests for:

1. JWT Token Security
2. Authentication Bypass Attempts
3. Permission Testing (accessing other users' images)
4. Input Validation and Sanitization
5. File Upload Security

Usage:
    python manage.py test tests.security.test_runner

Or run individual test suites:
    python manage.py test tests.security.test_jwt_security
    python manage.py test tests.security.test_auth_bypass
    python manage.py test tests.security.test_permissions
    python manage.py test tests.security.test_input_validation
    python manage.py test tests.security.test_file_uploads
"""

from tests.security.test_jwt_security import JWTSecurityTest
from tests.security.test_auth_bypass import AuthBypassTest
from tests.security.test_permissions import PermissionTest
from tests.security.test_input_validation import InputValidationTest
from tests.security.test_file_uploads import FileUploadSecurityTest


class SecurityTestSuite:
    """
    Comprehensive security test suite for the image processing service.

    This class serves as documentation for all security tests included in the suite.
    Each test class focuses on a specific area of security:

    1. JWTSecurityTest - Tests JWT token security, expiration, signature validation
    2. AuthBypassTest - Tests authentication bypass attempts and malformed requests
    3. PermissionTest - Tests user access controls and data isolation
    4. InputValidationTest - Tests input sanitization against injection attacks
    5. FileUploadSecurityTest - Tests file upload security and validation

    To run all tests:
        python manage.py test tests.security

    To run specific test categories:
        python manage.py test tests.security.test_jwt_security.JWTSecurityTest
        python manage.py test tests.security.test_auth_bypass.AuthBypassTest
        python manage.py test tests.security.test_permissions.PermissionTest
        python manage.py test tests.security.test_input_validation.InputValidationTest
        python manage.py test tests.security.test_file_uploads.FileUploadSecurityTest
    """

    @classmethod
    def get_test_classes(cls):
        """Return all security test classes"""
        return [
            JWTSecurityTest,
            AuthBypassTest,
            PermissionTest,
            InputValidationTest,
            FileUploadSecurityTest,
        ]

    @classmethod
    def get_test_descriptions(cls):
        """Return descriptions of each test suite"""
        return {
            "JWTSecurityTest": "Tests JWT token security including expiration, signature validation, and refresh token handling",
            "AuthBypassTest": "Tests authentication bypass attempts using malformed headers and invalid tokens",
            "PermissionTest": "Tests user access controls to ensure users can only access their own resources",
            "InputValidationTest": "Tests input validation and sanitization against SQL injection, XSS, and other attacks",
            "FileUploadSecurityTest": "Tests file upload security including type validation, size limits, and malicious content detection",
        }


# Make test classes available at module level for easy import
__all__ = [
    "JWTSecurityTest",
    "AuthBypassTest",
    "PermissionTest",
    "InputValidationTest",
    "FileUploadSecurityTest",
    "SecurityTestSuite",
]
