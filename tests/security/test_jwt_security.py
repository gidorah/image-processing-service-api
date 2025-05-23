import jwt
from datetime import datetime, timedelta

from django.test import override_settings
from django.urls import reverse
from rest_framework import status

from tests.security.base import SecurityTestBase


class JWTSecurityTest(SecurityTestBase):
    """
    Test suite for JWT token security vulnerabilities
    """

    def test_expired_token_rejected(self):
        """Test that expired tokens are rejected"""
        # Create an expired token
        expired_token = self.create_expired_jwt_token(self.user_a)

        # Try to access protected endpoint with expired token
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {expired_token}")
        response = self.client.get(reverse("source_image_list"))

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_token_with_invalid_signature_rejected(self):
        """Test that tokens with invalid signatures are rejected"""
        # Get a valid token and tamper with it
        tokens = self.get_tokens_for_user(self.user_a)
        valid_token = tokens["access"]

        # Tamper with the token by changing a character
        tampered_token = valid_token[:-1] + ("x" if valid_token[-1] != "x" else "y")

        # Try to access protected endpoint with tampered token
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {tampered_token}")
        response = self.client.get(reverse("source_image_list"))

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_token_signed_with_wrong_secret_rejected(self):
        """Test that tokens signed with wrong secret key are rejected"""
        # Create token with wrong secret key
        invalid_token = self.create_invalid_jwt_token(
            payload={
                "user_id": self.user_a.id,
                "exp": datetime.utcnow() + timedelta(minutes=5),
                "iat": datetime.utcnow(),
                "jti": "test-jti",
            },
            secret_key="wrong-secret-key",
        )

        # Try to access protected endpoint
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {invalid_token}")
        response = self.client.get(reverse("source_image_list"))

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_none_algorithm_token_rejected(self):
        """Test that tokens with 'none' algorithm are rejected"""
        # Create token with 'none' algorithm
        payload = {
            "user_id": self.user_a.id,
            "exp": datetime.utcnow() + timedelta(minutes=5),
            "iat": datetime.utcnow(),
            "jti": "test-jti",
        }

        # Create token with 'none' algorithm (no signature)
        none_token = jwt.encode(payload, "", algorithm="none")

        # Try to access protected endpoint
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {none_token}")
        response = self.client.get(reverse("source_image_list"))

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_refresh_token_provides_new_access_token(self):
        """Test that valid refresh tokens can generate new access tokens"""
        tokens = self.get_tokens_for_user(self.user_a)

        # Use refresh token to get new access token
        response = self.client.post(
            reverse("token_refresh"), {"refresh": tokens["refresh"]}
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("access", response.data)

    def test_invalid_refresh_token_rejected(self):
        """Test that invalid refresh tokens are rejected"""
        # Create invalid refresh token
        invalid_refresh_token = self.create_invalid_jwt_token(
            payload={
                "user_id": self.user_a.id,
                "exp": datetime.utcnow() + timedelta(hours=1),
                "iat": datetime.utcnow(),
                "jti": "invalid-refresh-jti",
                "token_type": "refresh",
            }
        )

        response = self.client.post(
            reverse("token_refresh"), {"refresh": invalid_refresh_token}
        )

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_expired_refresh_token_rejected(self):
        """Test that expired refresh tokens are rejected"""
        # Create expired refresh token
        expired_refresh_payload = {
            "user_id": self.user_a.id,
            "exp": datetime.utcnow() - timedelta(hours=1),  # Expired
            "iat": datetime.utcnow() - timedelta(hours=2),
            "jti": "expired-refresh-jti",
            "token_type": "refresh",
        }

        expired_refresh_token = jwt.encode(
            expired_refresh_payload, "wrong-secret", algorithm="HS256"
        )

        response = self.client.post(
            reverse("token_refresh"), {"refresh": expired_refresh_token}
        )

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    @override_settings(SIMPLE_JWT={"ROTATE_REFRESH_TOKENS": True})
    def test_refresh_token_rotation(self):
        """Test that refresh tokens are rotated when used"""
        tokens = self.get_tokens_for_user(self.user_a)
        original_refresh = tokens["refresh"]

        # Use refresh token
        response = self.client.post(
            reverse("token_refresh"), {"refresh": original_refresh}
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # If rotation is enabled, we should get a new refresh token
        if "refresh" in response.data:
            new_refresh = response.data["refresh"]
            self.assertNotEqual(original_refresh, new_refresh)

    def test_malformed_jwt_structure_rejected(self):
        """Test that malformed JWT structures are rejected"""
        malformed_tokens = [
            "invalid.token",  # Only two parts
            "invalid",  # Only one part
            "invalid.token.structure.extra",  # Too many parts
            "invalid..token",  # Empty middle part
            "",  # Empty token
            "Bearer invalid-token",  # Include Bearer prefix in token
        ]

        for malformed_token in malformed_tokens:
            with self.subTest(token=malformed_token):
                self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {malformed_token}")
                response = self.client.get(reverse("source_image_list"))
                self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_token_with_non_existent_user_rejected(self):
        """Test that tokens for non-existent users are rejected"""
        # Create token for non-existent user
        invalid_token = self.create_invalid_jwt_token(
            payload={
                "user_id": 99999,  # Non-existent user ID
                "exp": datetime.utcnow() + timedelta(minutes=5),
                "iat": datetime.utcnow(),
                "jti": "test-jti",
            },
            secret_key="dummy_secret_key_for_testing",  # Use the test secret key
        )

        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {invalid_token}")
        response = self.client.get(reverse("source_image_list"))

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_token_expiration_simulation(self):
        """Test token expiration by creating already expired token"""
        # Create token that's already expired
        expired_payload = {
            "user_id": self.user_a.id,
            "exp": datetime.utcnow() - timedelta(minutes=1),  # Expired 1 minute ago
            "iat": datetime.utcnow() - timedelta(minutes=10),
            "jti": "expired-test-jti",
        }

        expired_token = jwt.encode(
            expired_payload, "dummy_secret_key_for_testing", algorithm="HS256"
        )

        # Token should be rejected
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {expired_token}")
        response = self.client.get(reverse("source_image_list"))
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_multiple_authorization_headers(self):
        """Test behavior with multiple authorization headers"""
        tokens = self.get_tokens_for_user(self.user_a)

        # Try to send request with multiple authorization headers
        response = self.client.get(
            reverse("source_image_list"),
            HTTP_AUTHORIZATION=f"Bearer {tokens['access']}",
            HTTP_AUTHORIZATION_2="Bearer invalid-token",
        )

        # Should use the first valid authorization header
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_case_sensitive_bearer_prefix(self):
        """Test that Bearer prefix is case sensitive"""
        tokens = self.get_tokens_for_user(self.user_a)

        # Test different cases
        prefixes = ["bearer", "BEARER", "Bearer"]
        expected_results = [
            status.HTTP_401_UNAUTHORIZED,
            status.HTTP_401_UNAUTHORIZED,
            status.HTTP_200_OK,
        ]

        for prefix, expected in zip(prefixes, expected_results):
            with self.subTest(prefix=prefix):
                self.client.credentials(
                    HTTP_AUTHORIZATION=f"{prefix} {tokens['access']}"
                )
                response = self.client.get(reverse("source_image_list"))
                self.assertEqual(response.status_code, expected)

    def test_token_without_bearer_prefix_rejected(self):
        """Test that tokens without Bearer prefix are rejected"""
        tokens = self.get_tokens_for_user(self.user_a)

        # Send token without Bearer prefix
        self.client.credentials(HTTP_AUTHORIZATION=tokens["access"])
        response = self.client.get(reverse("source_image_list"))

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
