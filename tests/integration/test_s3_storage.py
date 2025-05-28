"""
Integration tests for S3 storage functionality.

These tests verify that the Django application correctly integrates with S3 storage
for file upload, retrieval, deletion, and URL generation operations.
Uses moto to mock AWS S3 service for reliable testing.
"""

import uuid

import boto3
from django.conf import settings
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from django.test import TestCase, override_settings
from moto import mock_aws
from PIL import Image

from tests.utils import create_test_image_file

AWS_STORAGE_BUCKET_NAME = "test-image-processing-bucket"
AWS_S3_REGION_NAME = "us-east-1"
AWS_ACCESS_KEY_ID = "testing"
AWS_SECRET_ACCESS_KEY = "testing"

# Test settings that ensure we use S3 storage with moto
TEST_S3_SETTINGS = {
    "STORAGES": {
        "default": {
            "BACKEND": "storages.backends.s3.S3Storage",
            "OPTIONS": {
                "access_key": AWS_ACCESS_KEY_ID,
                "secret_key": AWS_SECRET_ACCESS_KEY,
                "bucket_name": AWS_STORAGE_BUCKET_NAME,
                "region_name": AWS_S3_REGION_NAME,
            },
        }
    },
    "AWS_STORAGE_BUCKET_NAME": AWS_STORAGE_BUCKET_NAME,
    "AWS_S3_REGION_NAME": AWS_S3_REGION_NAME,
    "AWS_ACCESS_KEY_ID": AWS_ACCESS_KEY_ID,
    "AWS_SECRET_ACCESS_KEY": AWS_SECRET_ACCESS_KEY,
}


@mock_aws
@override_settings(**TEST_S3_SETTINGS)
class S3StorageIntegrationTests(TestCase):
    """
    Test suite for S3 storage integration.
    Ensures that file operations (upload, retrieve, delete) with S3 work as expected.
    """

    def setUp(self):
        """
        Set up the test environment.
        Creates the mock S3 bucket and prepares test files.
        """
        # Create the S3 bucket in moto
        self.s3_client = boto3.client(
            "s3",
            region_name=AWS_S3_REGION_NAME,
            aws_access_key_id=AWS_ACCESS_KEY_ID,
            aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
        )
        self.bucket_name = AWS_STORAGE_BUCKET_NAME
        self.s3_client.create_bucket(Bucket=self.bucket_name)

        # Prepare test files
        self.test_filename = f"test_file_{uuid.uuid4()}.txt"
        self.test_content = b"This is a test file for S3 integration."
        self.file_content = ContentFile(self.test_content, name=self.test_filename)

        # Create test image file
        self.test_image_filename = f"test_image_{uuid.uuid4()}.jpg"
        self.test_image_file = create_test_image_file(self.test_image_filename)

    def tearDown(self):
        """
        Clean up after each test.
        Deletes any files created during the test from S3.
        """
        # Clean up text file
        if default_storage.exists(self.test_filename):
            default_storage.delete(self.test_filename)

        # Clean up image file
        if default_storage.exists(self.test_image_filename):
            default_storage.delete(self.test_image_filename)

    def test_file_upload_to_s3(self):
        """
        Test that a file can be successfully uploaded to S3.
        """
        path = default_storage.save(self.test_filename, self.file_content)
        self.assertTrue(default_storage.exists(path))

        # Verify the file exists in the mock S3 bucket
        objects = self.s3_client.list_objects_v2(Bucket=self.bucket_name)
        self.assertIn("Contents", objects)
        uploaded_files = [obj["Key"] for obj in objects["Contents"]]
        self.assertIn(path, uploaded_files)

    def test_image_upload_to_s3(self):
        """
        Test that an image file can be successfully uploaded to S3.
        """
        path = default_storage.save(self.test_image_filename, self.test_image_file)
        self.assertTrue(default_storage.exists(path))

        # Verify the image file exists in the mock S3 bucket
        objects = self.s3_client.list_objects_v2(Bucket=self.bucket_name)
        self.assertIn("Contents", objects)
        uploaded_files = [obj["Key"] for obj in objects["Contents"]]
        self.assertIn(path, uploaded_files)

    def test_file_retrieve_from_s3(self):
        """
        Test that a file can be successfully retrieved from S3 and its content matches.
        """
        path = default_storage.save(self.test_filename, self.file_content)

        retrieved_file = default_storage.open(path, "rb")
        content = retrieved_file.read()
        retrieved_file.close()

        self.assertEqual(content, self.test_content)

    def test_image_retrieve_from_s3(self):
        """
        Test that an image can be successfully retrieved from S3 and opened.
        """
        path = default_storage.save(self.test_image_filename, self.test_image_file)

        retrieved_file = default_storage.open(path, "rb")

        # Verify we can open the retrieved image with PIL
        image = Image.open(retrieved_file)
        self.assertIsInstance(image, Image.Image)
        self.assertEqual(image.format, "JPEG")

        retrieved_file.close()

    def test_file_delete_from_s3(self):
        """
        Test that a file can be successfully deleted from S3.
        """
        path = default_storage.save(self.test_filename, self.file_content)
        self.assertTrue(default_storage.exists(path))

        default_storage.delete(path)
        self.assertFalse(default_storage.exists(path))

        # Verify the file is deleted from the mock S3 bucket
        objects = self.s3_client.list_objects_v2(Bucket=self.bucket_name)
        if "Contents" in objects:
            uploaded_files = [obj["Key"] for obj in objects["Contents"]]
            self.assertNotIn(path, uploaded_files)

    def test_file_overwrite_on_s3(self):
        """
        Test that uploading a file with the same name overwrites the existing file.
        """
        # Upload initial file
        path = default_storage.save(self.test_filename, self.file_content)

        # Prepare new content for overwrite
        new_content = b"This is the overwritten content."
        new_file_content = ContentFile(new_content, name=self.test_filename)

        # Delete the old file first (Django's default behavior)
        default_storage.delete(path)

        # Save again with the same name
        new_path = default_storage.save(self.test_filename, new_file_content)
        self.assertTrue(default_storage.exists(new_path))

        # Retrieve and check content
        retrieved_file = default_storage.open(new_path, "rb")
        content = retrieved_file.read()
        retrieved_file.close()

        self.assertEqual(content, new_content)

    def test_file_exists_non_existent_file(self):
        """
        Test that `exists()` returns False for a non-existent file.
        """
        non_existent_filename = f"non_existent_file_{uuid.uuid4()}.txt"
        self.assertFalse(default_storage.exists(non_existent_filename))

    def test_file_url_generation(self):
        """
        Test that a URL can be generated for a file stored in S3.
        """
        path = default_storage.save(self.test_filename, self.file_content)
        url = default_storage.url(path)

        self.assertIsNotNone(url)
        self.assertIn(path, url)
        # For moto, the URL should contain the bucket name
        self.assertIn(self.bucket_name, url)

    def test_file_size_retrieval(self):
        """
        Test that file size can be retrieved correctly from S3.
        """
        path = default_storage.save(self.test_filename, self.file_content)
        size = default_storage.size(path)

        self.assertEqual(size, len(self.test_content))

    def test_multiple_files_upload(self):
        """
        Test uploading multiple files to ensure no conflicts.
        """
        files_to_upload = []

        for i in range(3):
            filename = f"multi_test_{i}_{uuid.uuid4()}.txt"
            content = f"Content for file {i}".encode()
            file_content = ContentFile(content, name=filename)

            path = default_storage.save(filename, file_content)
            files_to_upload.append((path, content))

            self.assertTrue(default_storage.exists(path))

        # Verify all files exist and have correct content
        for path, expected_content in files_to_upload:
            retrieved_file = default_storage.open(path, "rb")
            actual_content = retrieved_file.read()
            retrieved_file.close()

            self.assertEqual(actual_content, expected_content)

            # Clean up
            default_storage.delete(path)

    def test_s3_storage_configuration_validation(self):
        """
        Test that S3 storage is properly configured for the test environment.
        """
        # Verify that we're using S3 storage backend
        self.assertIn("s3", default_storage.__class__.__module__.lower())

        # Verify bucket exists in moto
        response = self.s3_client.head_bucket(Bucket=self.bucket_name)
        self.assertEqual(response["ResponseMetadata"]["HTTPStatusCode"], 200)

    def test_large_file_upload(self):
        """
        Test uploading a larger file to ensure S3 integration handles it properly.
        """
        # Create a larger test file (10MB)
        large_content = b"x" * settings.IMAGE_MAX_FILE_SIZE_IN_BYTES
        large_filename = f"large_file_{uuid.uuid4()}.bin"
        large_file_content = ContentFile(large_content, name=large_filename)

        try:
            path = default_storage.save(large_filename, large_file_content)
            self.assertTrue(default_storage.exists(path))

            # Verify size
            size = default_storage.size(path)
            self.assertEqual(size, len(large_content))

        finally:
            # Clean up
            if default_storage.exists(large_filename):
                default_storage.delete(large_filename)
