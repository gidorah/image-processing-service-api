import base64
from datetime import datetime, timedelta
from io import BytesIO
from unittest.mock import patch

import jwt
from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from PIL import Image
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

from api.models import SourceImage

User = get_user_model()

# Override cache settings to avoid rate limiting during tests
CACHE_OVERRIDE = {
    "default": {
        "BACKEND": "django.core.cache.backends.dummy.DummyCache",
    }
}


@override_settings(CACHES=CACHE_OVERRIDE)
class SecurityTestBase(TestCase):
    """
    Base test class for security tests with common utilities
    """

    def setUp(self):
        """Set up test data for security tests"""
        self.client = APIClient()

        # Create test users
        self.user_a = User.objects.create_user(
            username="user_a", email="user_a@test.com", password="test_password_123!"
        )

        self.user_b = User.objects.create_user(
            username="user_b", email="user_b@test.com", password="test_password_456!"
        )

        # Create an admin user
        self.admin_user = User.objects.create_superuser(
            username="admin", email="admin@test.com", password="admin_password_789!"
        )

    def get_tokens_for_user(self, user):
        """Generate JWT tokens for a user"""
        refresh = RefreshToken.for_user(user)
        return {
            "refresh": str(refresh),
            "access": str(refresh.access_token),
        }

    def authenticate_user(self, user):
        """Authenticate a user with the test client"""
        tokens = self.get_tokens_for_user(user)
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {tokens['access']}")
        return tokens

    def clear_authentication(self):
        """Clear authentication from the test client"""
        self.client.credentials()

    def create_test_image_file(
        self, filename="test.jpg", format="JPEG", size=(100, 100)
    ):
        """Create a test image file"""
        image = Image.new("RGB", size, color="red")
        image_io = BytesIO()
        image.save(image_io, format=format)
        image_io.seek(0)

        return SimpleUploadedFile(
            filename, image_io.getvalue(), content_type=f"image/{format.lower()}"
        )

    def create_test_source_image(self, owner, filename="test.jpg") -> SourceImage:
        """Create a test source image for a user"""
        image_file = self.create_test_image_file(filename)

        return SourceImage.objects.create(
            file=image_file,
            file_name=filename,
            description="Test image description",
            metadata={"test": "data"},
            owner=owner,
        )

    def create_invalid_jwt_token(
        self, payload=None, secret_key=None, algorithm="HS256"
    ):
        """Create an invalid JWT token for testing"""
        if payload is None:
            payload = {
                "user_id": 999,
                "exp": datetime.utcnow() + timedelta(minutes=5),
                "iat": datetime.utcnow(),
                "jti": "invalid-jti",
            }

        if secret_key is None:
            secret_key = "wrong-secret-key"

        return jwt.encode(payload, secret_key, algorithm=algorithm)

    def create_expired_jwt_token(self, user):
        """Create an expired JWT token for testing"""
        payload = {
            "user_id": user.id,
            "exp": datetime.utcnow() - timedelta(minutes=5),  # Expired 5 minutes ago
            "iat": datetime.utcnow() - timedelta(minutes=10),
            "jti": "expired-jti",
        }

        return jwt.encode(payload, settings.SECRET_KEY, algorithm="HS256")

    def create_malformed_file(self, filename, content, content_type):
        """Create a malformed file for testing"""
        return SimpleUploadedFile(filename, content, content_type=content_type)

    def create_large_file(self, filename="large.jpg", size_mb=50):
        """Create a large file for testing file size limits"""
        content = b"x" * (size_mb * 1024 * 1024)
        return SimpleUploadedFile(filename, content, content_type="image/jpeg")

    def encode_basic_auth(self, username, password):
        """Encode basic auth credentials"""
        credentials = f"{username}:{password}"
        encoded = base64.b64encode(credentials.encode()).decode()
        return f"Basic {encoded}"
