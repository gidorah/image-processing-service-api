import unittest
import boto3
from moto import mock_aws
from django.conf import settings

# Configure Django settings if not already configured
if not settings.configured:
    settings.configure(
        AWS_ACCESS_KEY_ID='testing',
        AWS_SECRET_ACCESS_KEY='testing',
        AWS_S3_REGION_NAME='us-east-1',
        AWS_STORAGE_BUCKET_NAME='test-bucket',
        # Add other necessary Django settings here
    )

@mock_aws
class TestS3Storage(unittest.TestCase):

    def setUp(self):
        """Set up the test environment for S3."""
        self.s3_client = boto3.client(
            's3',
            region_name=settings.AWS_S3_REGION_NAME,
            aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
            aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY
        )
        self.bucket_name = settings.AWS_STORAGE_BUCKET_NAME
        # Create the mock S3 bucket
        self.s3_client.create_bucket(Bucket=self.bucket_name)

    def tearDown(self):
        """Clean up the S3 resources after tests."""
        # Delete all objects in the bucket
        objects = self.s3_client.list_objects_v2(Bucket=self.bucket_name)
        if 'Contents' in objects:
            for obj in objects['Contents']:
                self.s3_client.delete_object(Bucket=self.bucket_name, Key=obj['Key'])
        # Delete the bucket itself
        self.s3_client.delete_bucket(Bucket=self.bucket_name)

    def test_upload_file_to_s3(self):
        """Test uploading a file to S3."""
        file_content = b'This is a test file.'
        file_key = 'test_upload.txt'
        
        self.s3_client.put_object(Bucket=self.bucket_name, Key=file_key, Body=file_content)
        
        # Verify the file was uploaded
        response = self.s3_client.get_object(Bucket=self.bucket_name, Key=file_key)
        uploaded_content = response['Body'].read()
        self.assertEqual(uploaded_content, file_content)

    def test_retrieve_file_from_s3(self):
        """Test retrieving a file from S3."""
        file_content = b'This is another test file.'
        file_key = 'test_retrieve.txt'
        
        # First, upload a file to retrieve
        self.s3_client.put_object(Bucket=self.bucket_name, Key=file_key, Body=file_content)
        
        # Retrieve the file
        response = self.s3_client.get_object(Bucket=self.bucket_name, Key=file_key)
        retrieved_content = response['Body'].read()
        self.assertEqual(retrieved_content, file_content)

    def test_delete_file_from_s3(self):
        """Test deleting a file from S3."""
        file_content = b'This file will be deleted.'
        file_key = 'test_delete.txt'
        
        # Upload the file
        self.s3_client.put_object(Bucket=self.bucket_name, Key=file_key, Body=file_content)
        
        # Delete the file
        self.s3_client.delete_object(Bucket=self.bucket_name, Key=file_key)
        
        # Verify the file was deleted (trying to get it should raise an error)
        with self.assertRaises(self.s3_client.exceptions.NoSuchKey):
            self.s3_client.get_object(Bucket=self.bucket_name, Key=file_key)

    def test_upload_different_file_types(self):
        """Test uploading different types of files (e.g., text, binary)."""
        files_to_test = {
            'text_file.txt': (b'Simple text content.', 'text/plain'),
            'binary_file.bin': (b'\x00\x01\x02\x03\x04', 'application/octet-stream')
        }
        
        for file_key, (content, content_type) in files_to_test.items():
            with self.subTest(file=file_key):
                self.s3_client.put_object(
                    Bucket=self.bucket_name,
                    Key=file_key,
                    Body=content,
                    ContentType=content_type
                )
                response = self.s3_client.get_object(Bucket=self.bucket_name, Key=file_key)
                self.assertEqual(response['Body'].read(), content)
                self.assertEqual(response['ContentType'], content_type)

    def test_list_files_in_bucket(self):
        """Test listing files in the S3 bucket."""
        # Upload a few files
        self.s3_client.put_object(Bucket=self.bucket_name, Key='file1.txt', Body=b'content1')
        self.s3_client.put_object(Bucket=self.bucket_name, Key='file2.txt', Body=b'content2')
        self.s3_client.put_object(Bucket=self.bucket_name, Key='folder/file3.txt', Body=b'content3')
        
        response = self.s3_client.list_objects_v2(Bucket=self.bucket_name)
        self.assertIn('Contents', response)
        
        # Check if all uploaded files are listed
        found_keys = {item['Key'] for item in response['Contents']}
        expected_keys = {'file1.txt', 'file2.txt', 'folder/file3.txt'}
        self.assertEqual(found_keys, expected_keys)

if __name__ == '__main__':
    unittest.main()
