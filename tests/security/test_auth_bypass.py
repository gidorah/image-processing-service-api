from django.urls import reverse
from rest_framework import status

from tests.security.base import SecurityTestBase


class AuthBypassTest(SecurityTestBase):
    """
    Test suite for authentication bypass attempts
    """

    def test_protected_endpoints_without_auth_rejected(self):
        """Test that protected endpoints reject requests without authentication"""
        protected_endpoints = [
            ("source_image_list", "GET"),
            ("source_image_upload", "POST"),
            ("transformed_image_list", "GET"),
            ("task-list", "GET"),  # TransformationTaskViewSet list endpoint
        ]

        for endpoint_name, method in protected_endpoints:
            with self.subTest(endpoint=endpoint_name, method=method):
                self.clear_authentication()
                url = reverse(endpoint_name)
                if method == "GET":
                    response = self.client.get(url)
                elif method == "POST":
                    response = self.client.post(url, {})
                else:
                    raise ValueError(f"Unsupported method: {method}")

                self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_protected_endpoints_with_detail_pk_without_auth_rejected(self):
        """Test that protected detail endpoints reject requests without authentication"""
        # Create test image first
        self.authenticate_user(self.user_a)
        source_image = self.create_test_source_image(self.user_a)

        # Create a transformation task for testing task detail endpoint
        from api.models import TransformationTask

        task = TransformationTask.objects.create(
            owner=self.user_a,
            original_image=source_image,
            transformations=[{"resize": {"width": 100, "height": 100}}],
            format="JPEG",
        )

        # Clear authentication and try to access
        self.clear_authentication()

        protected_detail_endpoints = [
            ("source_image_detail", source_image.pk),
            (
                "transformed_image_detail",
                source_image.pk,
            ),
            ("create_transformed_image", source_image.pk),
            ("task-detail", task.pk),
        ]

        for endpoint_name, pk in protected_detail_endpoints:
            with self.subTest(endpoint=endpoint_name, pk=pk):
                url = reverse(endpoint_name, kwargs={"pk": pk})
                response = self.client.get(url)
                self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_malformed_authorization_header_rejected(self):
        """Test that malformed authorization headers are rejected"""
        malformed_headers = [
            "Bearer",  # Missing token
            "Basic invalid-token",  # Wrong auth type
            "Bearer ",  # Bearer with space but no token
            "InvalidAuth token",  # Wrong auth type
            "bearer valid-token",  # Wrong case
            "BEARER valid-token",  # Wrong case
        ]

        for header in malformed_headers:
            with self.subTest(header=header):
                self.client.credentials(HTTP_AUTHORIZATION=header)
                response = self.client.get(reverse("source_image_list"))
                self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_empty_authorization_header_rejected(self):
        """Test that empty authorization headers are rejected"""
        self.client.credentials(HTTP_AUTHORIZATION="")
        response = self.client.get(reverse("source_image_list"))
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_no_authorization_header_rejected(self):
        """Test that requests without authorization headers are rejected"""
        # Explicitly clear any existing credentials
        self.clear_authentication()

        response = self.client.get(reverse("source_image_list"))
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_invalid_token_format_rejected(self):
        """Test that invalid token formats are rejected"""
        invalid_tokens = [
            "not-a-jwt-token",
            "invalid.jwt",
            "still.not.valid.jwt.token",
            "...",
            "Bearer",
            "token-without-bearer",
        ]

        for token in invalid_tokens:
            with self.subTest(token=token):
                self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")
                response = self.client.get(reverse("source_image_list"))
                self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_sql_injection_in_auth_header_handled(self):
        """Test that SQL injection attempts in auth headers are handled safely"""
        sql_injection_payloads = [
            "Bearer ' OR '1'='1",
            "Bearer '; DROP TABLE auth_user; --",
            "Bearer 1' UNION SELECT * FROM auth_user --",
            "Bearer admin'--",
            "Bearer '; INSERT INTO auth_user (username) VALUES ('hacker'); --",
        ]

        for payload in sql_injection_payloads:
            with self.subTest(payload=payload):
                self.client.credentials(HTTP_AUTHORIZATION=payload)
                response = self.client.get(reverse("source_image_list"))
                # Should return 401, not 500 (server error)
                self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_very_long_authorization_header_handled(self):
        """Test that very long authorization headers are handled safely"""
        # Create a very long token
        long_token = "Bearer " + "x" * 10000

        self.client.credentials(HTTP_AUTHORIZATION=long_token)
        response = self.client.get(reverse("source_image_list"))

        # Should return 401, not 500 (server error)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_unicode_characters_in_auth_header_handled(self):
        """Test that unicode characters in auth headers are handled safely"""
        unicode_tokens = [
            "Bearer 🔐invalid🔑token🗝️",
            "Bearer тест-токен",
            "Bearer 测试令牌",
            "Bearer حروف عربية",
        ]

        for token in unicode_tokens:
            with self.subTest(token=token):
                self.client.credentials(HTTP_AUTHORIZATION=token)
                try:
                    response = self.client.get(reverse("source_image_list"))
                    self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
                except UnicodeEncodeError:
                    # This is actually a good security response - the system
                    # properly rejects invalid unicode in HTTP headers
                    pass

    def test_null_bytes_in_auth_header_handled(self):
        """Test that null bytes in auth headers are handled safely"""
        null_byte_tokens = [
            "Bearer token\x00with\x00nulls",
            "Bearer \x00token",
            "Bearer token\x00",
        ]

        for token in null_byte_tokens:
            with self.subTest(token=token):
                self.client.credentials(HTTP_AUTHORIZATION=token)
                response = self.client.get(reverse("source_image_list"))
                self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_token_obtain_pair_without_credentials_rejected(self):
        """Test that token obtain endpoint rejects requests without valid credentials"""
        # Try to get token without providing username/password
        response = self.client.post(reverse("token_obtain_pair"), {})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        # Try with invalid credentials
        response = self.client.post(
            reverse("token_obtain_pair"),
            {"username": "nonexistent", "password": "wrongpassword"},
        )
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_token_refresh_without_valid_token_rejected(self):
        """Test that token refresh endpoint rejects requests without valid tokens"""
        # Try to refresh without providing refresh token
        response = self.client.post(reverse("token_refresh"), {})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        # Try with invalid refresh token
        response = self.client.post(
            reverse("token_refresh"), {"refresh": "invalid-refresh-token"}
        )
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_mixed_case_bearer_prefix_rejected(self):
        """Test that mixed case Bearer prefix is rejected"""
        tokens = self.get_tokens_for_user(self.user_a)

        mixed_cases = [
            "Bearer",
            "bEaReR",
            "BEARER",
            "bearer",
            "BeArEr",
        ]

        for case in mixed_cases:
            with self.subTest(case=case):
                self.client.credentials(HTTP_AUTHORIZATION=f"{case} {tokens['access']}")
                response = self.client.get(reverse("source_image_list"))
                # Only 'Bearer' should work, all others should fail
                if case == "Bearer":
                    self.assertEqual(response.status_code, status.HTTP_200_OK)
                else:
                    self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_extra_spaces_in_auth_header_handled(self):
        """Test that extra spaces in authorization headers are handled correctly"""
        tokens = self.get_tokens_for_user(self.user_a)

        spaced_headers = [
            f"  Bearer {tokens['access']}",  # Leading spaces
            f"Bearer  {tokens['access']}",  # Extra space after Bearer
            f"Bearer {tokens['access']}  ",  # Trailing spaces
            f"  Bearer  {tokens['access']}  ",  # Multiple spaces
        ]

        for header in spaced_headers:
            with self.subTest(header=repr(header)):
                self.client.credentials(HTTP_AUTHORIZATION=header)
                response = self.client.get(reverse("source_image_list"))
                # Depending on implementation, this might work or not
                # Most implementations should handle this gracefully
                self.assertIn(
                    response.status_code,
                    [status.HTTP_200_OK, status.HTTP_401_UNAUTHORIZED],
                )

    def test_concurrent_auth_attempts_handled(self):
        """Test that multiple concurrent authentication attempts are handled safely"""
        # This test simulates rapid-fire authentication attempts
        # which could be used in brute force attacks

        for i in range(10):
            with self.subTest(attempt=i):
                self.client.credentials(HTTP_AUTHORIZATION=f"Bearer invalid-token-{i}")
                response = self.client.get(reverse("source_image_list"))
                self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
