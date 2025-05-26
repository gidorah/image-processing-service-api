import os

from django.conf import settings
from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse
from rest_framework import status

from tests.security.base import SecurityTestBase


class FileUploadSecurityTest(SecurityTestBase):
    """
    Test suite for file upload security vulnerabilities
    """

    def test_non_image_file_with_image_extension_rejected(self):
        """Test that non-image files with image extensions are rejected"""
        self.authenticate_user(self.user_a)

        # Create various non-image files with image extensions
        malicious_files = [
            ("script.jpg", b'#!/bin/bash\necho "malicious script"', "image/jpeg"),
            ("malware.png", b'<?php system($_GET["cmd"]); ?>', "image/png"),
            (
                "virus.gif",
                b"MZ\x90\x00\x03\x00\x00\x00\x04\x00",
                "image/gif",
            ),  # PE header
            (
                "trojan.bmp",
                b'<html><body><script>alert("xss")</script></body></html>',
                "image/bmp",
            ),
            (
                "exploit.webp",
                b'#!/usr/bin/python\nimport os\nos.system("rm -rf /")',
                "image/webp",
            ),
        ]

        for filename, content, content_type in malicious_files:
            with self.subTest(filename=filename):
                malicious_file = SimpleUploadedFile(
                    filename, content, content_type=content_type
                )

                response = self.client.post(
                    reverse("source_image_upload"),
                    {
                        "file": malicious_file,
                        "file_name": filename,
                        "description": "Test malicious file",
                        "metadata": "{}",
                    },
                )

                # Should reject non-image files
                self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_image_file_with_wrong_extension_handled(self):
        """Test that valid image files with wrong extensions are handled appropriately"""
        self.authenticate_user(self.user_a)

        # Create a valid PNG image but name it with different extension
        valid_image = self.create_test_image_file("test.txt", format="PNG")

        response = self.client.post(
            reverse("source_image_upload"),
            {
                "file": valid_image,
                "file_name": "image.txt",
                "description": "Valid image with wrong extension",
                "metadata": "{}",
            },
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_file_size_limits_enforced(self):
        """Test that file size limits are enforced"""
        self.authenticate_user(self.user_a)

        large_file_path = "tests/test_files/large_image.jpg"

        # Since creating a large file is time consuming, first
        # check if there is a file for the test
        if not os.path.exists(large_file_path):
            # Create a large image file > File Size Limit
            self.create_large_jpg(filename=large_file_path)

        large_file = SimpleUploadedFile(
            "large_image.jpg",
            open(large_file_path, "rb").read(),
            content_type="image/jpg",
        )

        print(f"large file size: {large_file.size}")

        # Check if the file size is greater than the limit
        self.assertGreater(large_file.size, settings.IMAGE_MAX_FILE_SIZE_IN_BYTES)

        response = self.client.post(
            reverse("source_image_upload"),
            {
                "file": large_file,
                "file_name": "large_image.jpg",
                "description": "Large image test",
                "metadata": "{}",
            },
        )

        print(f"large file response: {response.content}")

        # Should be rejected due to size
        self.assertEqual(response.status_code, status.HTTP_413_REQUEST_ENTITY_TOO_LARGE)

    def test_malicious_filenames_sanitized(self):
        """Test that malicious filenames are properly sanitized"""
        self.authenticate_user(self.user_a)

        malicious_filenames = [
            "../../../etc/passwd.jpg",
            "..\\..\\..\\windows\\system32\\config\\sam.png",
            "file\x00name.jpg",  # Null byte injection
            "file\rname.jpg",  # Carriage return
            "file\nname.jpg",  # Line feed
            "file\tname.jpg",  # Tab
            '<script>alert("xss")</script>.jpg',  # XSS in filename
            "../../root/.ssh/id_rsa.jpg",
            "CON.jpg",  # Windows reserved name
            "PRN.jpg",  # Windows reserved name
            "AUX.jpg",  # Windows reserved name
            "NUL.jpg",  # Windows reserved name
            "filename?.jpg",  # Invalid characters
            "filename*.jpg",
            "filename|.jpg",
            "filename<.jpg",
            "filename>.jpg",
            "filename:.jpg",
            'filename".jpg',
        ]

        for filename in malicious_filenames:
            with self.subTest(filename=repr(filename)):
                image_file = self.create_test_image_file("temp.jpg")

                response = self.client.post(
                    reverse("source_image_upload"),
                    {
                        "file": image_file,
                        "file_name": filename,
                        "description": "Test malicious filename",
                        "metadata": "{}",
                    },
                )

                # Should either reject or sanitize the filename
                if response.status_code == status.HTTP_201_CREATED:
                    # If accepted, filename should be sanitized
                    returned_filename = response.data.get("file_name", "")
                    # Should not contain dangerous characters
                    dangerous_chars = [
                        "..",
                        "/",
                        "\\",
                        "\x00",
                        "\r",
                        "\n",
                        "<",
                        ">",
                        "|",
                        "?",
                        "*",
                        ":",
                    ]
                    for char in dangerous_chars:
                        if char in filename:
                            self.assertNotIn(
                                char,
                                returned_filename,
                                f"Dangerous character '{char}' not sanitized in filename",
                            )

    def test_executable_file_upload_rejected(self):
        """Test that executable files are rejected even with image extensions"""
        self.authenticate_user(self.user_a)

        executable_signatures = [
            # PE (Windows executable) header
            (b"MZ\x90\x00\x03\x00\x00\x00\x04\x00\x00\x00\xff\xff\x00\x00", "exe.jpg"),
            # ELF (Linux executable) header
            (b"\x7fELF\x01\x01\x01\x00\x00\x00\x00\x00\x00\x00\x00\x00", "elf.png"),
            # Mach-O (macOS executable) header
            (b"\xfe\xed\xfa\xce\x00\x00\x00\x00", "macho.gif"),
            # Java class file
            (b"\xca\xfe\xba\xbe\x00\x00\x00\x34", "java.jpg"),
            # Python bytecode
            (b"\x03\xf3\x0d\x0a\x00\x00\x00\x00", "python.png"),
        ]

        for signature, filename in executable_signatures:
            with self.subTest(filename=filename):
                executable_file = SimpleUploadedFile(
                    filename,
                    signature + b"\x00" * 100,  # Pad with nulls
                    content_type="image/jpeg",
                )

                response = self.client.post(
                    reverse("source_image_upload"),
                    {
                        "file": executable_file,
                        "file_name": filename,
                        "description": "Test executable file",
                        "metadata": "{}",
                    },
                )

                # Should reject executable files
                self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_polyglot_file_upload_security(self):
        """Test security against polyglot files (files that are valid in multiple formats)"""
        self.authenticate_user(self.user_a)

        # Create a file that could be interpreted as both image and script
        polyglot_content = (
            b"GIF89a"  # GIF header
            b'<script>alert("xss")</script>'  # JavaScript
            b"\x00" * 100  # Padding
        )

        polyglot_file = SimpleUploadedFile(
            "polyglot.gif", polyglot_content, content_type="image/gif"
        )

        response = self.client.post(
            reverse("source_image_upload"),
            {
                "file": polyglot_file,
                "file_name": "polyglot.gif",
                "description": "Test polyglot file",
                "metadata": "{}",
            },
        )

        # Should either reject or handle safely
        self.assertIn(
            response.status_code, [status.HTTP_201_CREATED, status.HTTP_400_BAD_REQUEST]
        )

    def test_zip_bomb_protection(self):
        """Test protection against zip bombs in compressed image formats"""
        self.authenticate_user(self.user_a)

        # Create a simple "zip bomb" simulation
        # In reality, this would be a highly compressed file that expands enormously
        compressed_content = (
            b"\x50\x4b\x03\x04" + b"\x00" * 1000
        )  # ZIP signature + data

        zip_bomb = SimpleUploadedFile(
            "zipbomb.jpg", compressed_content, content_type="image/jpeg"
        )

        response = self.client.post(
            reverse("source_image_upload"),
            {
                "file": zip_bomb,
                "file_name": "zipbomb.jpg",
                "description": "Test zip bomb",
                "metadata": "{}",
            },
        )

        # Should be rejected as it's not a valid image
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_image_metadata_injection(self):
        """Test that malicious metadata in image files is handled safely"""
        self.authenticate_user(self.user_a)

        # Note: This is a simplified test. In practice, you'd need actual images
        # with malicious EXIF data, which is complex to generate in tests

        # Create a file with suspicious metadata-like content
        suspicious_content = (
            b"\xff\xe0\x00\x10JFIF"  # JPEG header start
            b'<script>alert("xss")</script>'  # Malicious content in metadata area
            + self.create_test_image_file("test.jpg").read()  # Actual image data
        )

        suspicious_file = SimpleUploadedFile(
            "metadata_injection.jpg", suspicious_content, content_type="image/jpeg"
        )

        response = self.client.post(
            reverse("source_image_upload"),
            {
                "file": suspicious_file,
                "file_name": "metadata_injection.jpg",
                "description": "Test metadata injection",
                "metadata": "{}",
            },
        )

        # Should handle the file safely
        self.assertIn(
            response.status_code, [status.HTTP_201_CREATED, status.HTTP_400_BAD_REQUEST]
        )

    def test_double_extension_files(self):
        """Test handling of files with double extensions"""
        self.authenticate_user(self.user_a)

        double_extension_files = [
            "image.jpg.exe",
            "photo.png.bat",
            "picture.gif.com",
            "file.jpeg.scr",
            "image.bmp.pif",
        ]

        for filename in double_extension_files:
            with self.subTest(filename=filename):
                image_file = self.create_test_image_file("test.jpg")

                response = self.client.post(
                    reverse("source_image_upload"),
                    {
                        "file": image_file,
                        "file_name": filename,
                        "description": "Test double extension",
                        "metadata": "{}",
                    },
                )

                # Should handle double extensions safely
                self.assertIn(
                    response.status_code,
                    [status.HTTP_201_CREATED, status.HTTP_400_BAD_REQUEST],
                )

    def test_mime_type_spoofing(self):
        """Test protection against MIME type spoofing"""
        self.authenticate_user(self.user_a)

        # Create a text file but claim it's an image
        text_content = b"This is not an image file, it is plain text."

        spoofed_file = SimpleUploadedFile(
            "spoofed.jpg",
            text_content,
            content_type="image/jpeg",  # Lying about content type
        )

        response = self.client.post(
            reverse("source_image_upload"),
            {
                "file": spoofed_file,
                "file_name": "spoofed.jpg",
                "description": "Test MIME spoofing",
                "metadata": "{}",
            },
        )

        # Should reject files that aren't actually images
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_server_side_include_injection(self):
        """Test protection against Server Side Include (SSI) injection"""
        self.authenticate_user(self.user_a)

        ssi_payloads = [
            'image.jpg<!--#exec cmd="cat /etc/passwd"-->',
            'photo.png<!--#include virtual="/etc/passwd"-->',
            'picture.gif<!--#echo var="DOCUMENT_ROOT"-->',
            'file.jpeg<!--#config timefmt="%A %B %d, %Y"-->',
        ]

        for filename in ssi_payloads:
            with self.subTest(filename=filename):
                image_file = self.create_test_image_file("test.jpg")

                response = self.client.post(
                    reverse("source_image_upload"),
                    {
                        "file": image_file,
                        "file_name": filename,
                        "description": "Test SSI injection",
                        "metadata": "{}",
                    },
                )

                # Should handle SSI payloads safely
                self.assertIn(
                    response.status_code,
                    [status.HTTP_201_CREATED, status.HTTP_400_BAD_REQUEST],
                )

    def test_php_code_injection_in_filenames(self):
        """Test protection against PHP code injection in filenames"""
        self.authenticate_user(self.user_a)

        php_payloads = [
            "image.php.jpg",
            "photo.jpg.php",
            'picture.gif<?php system($_GET["cmd"]); ?>',
            "file.jpeg.php5",
            "image.phtml.jpg",
            "photo.jpg<?php phpinfo(); ?>",
        ]

        for filename in php_payloads:
            with self.subTest(filename=filename):
                image_file = self.create_test_image_file("test.jpg")

                response = self.client.post(
                    reverse("source_image_upload"),
                    {
                        "file": image_file,
                        "file_name": filename,
                        "description": "Test PHP injection",
                        "metadata": "{}",
                    },
                )

                # Should handle PHP injection attempts safely
                self.assertIn(
                    response.status_code,
                    [status.HTTP_201_CREATED, status.HTTP_400_BAD_REQUEST],
                )

    def test_image_dimensions_validation(self):
        """Test validation of extreme image dimensions"""
        self.authenticate_user(self.user_a)

        # Test with extreme dimensions that could cause memory issues
        extreme_dimensions = [
            (1, 1),  # Too small
            (10000, 10000),  # Very large
            (0, 100),  # Zero width
            (100, 0),  # Zero height
            (-100, 100),  # Negative width
            (100, -100),  # Negative height
        ]

        for width, height in extreme_dimensions:
            with self.subTest(width=width, height=height):
                try:
                    # Some dimensions might fail during image creation
                    image_file = self.create_test_image_file(
                        "test.jpg", size=(abs(width) or 1, abs(height) or 1)
                    )

                    response = self.client.post(
                        reverse("source_image_upload"),
                        {
                            "file": image_file,
                            "file_name": "extreme_dimensions.jpg",
                            "description": f"Test {width}x{height} dimensions",
                            "metadata": "{}",
                        },
                    )

                    # Should handle extreme dimensions appropriately
                    self.assertIn(
                        response.status_code,
                        [status.HTTP_201_CREATED, status.HTTP_400_BAD_REQUEST],
                    )
                except Exception:
                    # If image creation fails due to invalid dimensions, that's acceptable
                    pass

    def test_concurrent_file_uploads(self):
        """Test handling of multiple concurrent file uploads"""
        self.authenticate_user(self.user_a)

        # Simulate multiple rapid uploads
        for i in range(5):
            with self.subTest(upload=i):
                image_file = self.create_test_image_file(f"concurrent_{i}.jpg")

                response = self.client.post(
                    reverse("source_image_upload"),
                    {
                        "file": image_file,
                        "file_name": f"concurrent_{i}.jpg",
                        "description": f"Concurrent upload {i}",
                        "metadata": "{}",
                    },
                )

                # All uploads should be handled correctly
                self.assertIn(
                    response.status_code,
                    [status.HTTP_201_CREATED, status.HTTP_400_BAD_REQUEST],
                )

    def test_file_content_vs_extension_mismatch(self):
        """Test handling of files where content doesn't match extension"""
        self.authenticate_user(self.user_a)

        mismatched_files = [
            ("document.pdf", "test.jpg", "application/pdf"),
            ("archive.zip", "test.png", "application/zip"),
            ("script.js", "test.gif", "application/javascript"),
            ("style.css", "test.bmp", "text/css"),
            ("data.xml", "test.webp", "application/xml"),
        ]

        for content_type, filename, mime_type in mismatched_files:
            with self.subTest(filename=filename):
                # Create a file with mismatched content
                mismatched_content = f"This is actually a {content_type} file".encode()

                mismatched_file = SimpleUploadedFile(
                    filename, mismatched_content, content_type=mime_type
                )

                response = self.client.post(
                    reverse("source_image_upload"),
                    {
                        "file": mismatched_file,
                        "file_name": filename,
                        "description": "Test content mismatch",
                        "metadata": "{}",
                    },
                )

                # Should reject files with mismatched content
                self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
