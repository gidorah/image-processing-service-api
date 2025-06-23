"""End-to-end test module for complete user flows."""

from io import BytesIO

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import override_settings
from django.urls import reverse
from PIL import Image
from rest_framework import status
from rest_framework.test import APITestCase

from api.models import (
    SourceImage,
    TaskStatus,
    TransformationTask,
    TransformedImage,
    User,
)

# Override cache settings to avoid rate limiting in tests
CACHE_OVERRIDE = {
    "CACHES": {
        "default": {
            "BACKEND": "django.core.cache.backends.dummy.DummyCache",
        }
    }
}


@override_settings(CACHES=CACHE_OVERRIDE["CACHES"])
class CompleteUserFlowTests(APITestCase):
    """End-to-end test case that verifies the complete user flow."""

    def setUp(self):
        """Set up test data."""
        self.username = "testuser"
        self.password = "TestPass123!"
        self.email = "testuser@example.com"

        self.registration_data = {
            "username": self.username,
            "email": self.email,
            "password1": self.password,
            "password2": self.password,
        }
        self.login_data = {
            "username": self.username,
            "password": self.password,
        }

        # Create a test image
        image = Image.new("RGB", (100, 100), color="red")
        buffer = BytesIO()
        image.save(buffer, format="JPEG")
        buffer.seek(0)
        self.test_image = SimpleUploadedFile(
            name="test_image.jpg", content=buffer.read(), content_type="image/jpeg"
        )

        self.image_description = "Test image for transformation"

    def test_complete_user_flow(self):
        """Test the complete user flow: registration → login → upload → transform."""
        # 1. User Registration
        register_url = reverse("rest_register")
        response = self.client.post(register_url, self.registration_data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        user = User.objects.filter(username=self.username)
        self.assertTrue(user.exists())

        # 2. User Login
        login_url = reverse("rest_login")
        response = self.client.post(login_url, self.login_data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # With cookie-based auth, tokens are in HttpOnly cookies, not the response body
        self.assertNotIn("token", response.data)
        self.assertIn("access", response.cookies)
        self.assertIn("refresh", response.cookies)

        # The test client will automatically handle the session cookies for subsequent
        # requests, so no need to manually set the Authorization header.

        # 3. Image Upload
        upload_url = reverse("source_image_upload")
        upload_data = {
            "file": self.test_image,
            "file_name": "test_image",
            "description": self.image_description,
        }
        response = self.client.post(upload_url, upload_data, format="multipart")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        source_images = SourceImage.objects.filter(file_name="test_image")
        self.assertTrue(source_images.exists())
        source_image = source_images.first()

        # 4. Create Transformation
        create_transform_url = reverse(
            "create_transformed_image", kwargs={"pk": source_image.pk}
        )
        transform_data = {
            "transformations": [
                {"operation": "resize", "params": {"width": 50, "height": 50}},
                {"operation": "apply_filter", "params": {"grayscale": True}},
            ]
        }
        response = self.client.post(create_transform_url, transform_data, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        task_id = response.data["id"]

        # 5. Verify task creation
        get_transform_url = reverse("task-detail", kwargs={"pk": task_id})
        response = self.client.get(get_transform_url)

        # Since we force celery to run synchronously in tests,
        # we can check the success status directly
        self.assertEqual(response.data["status"], TaskStatus.SUCCESS)
        self.assertEqual(len(response.data["transformations"]), 2)

        transformed_image_id = response.data["result_image"]
        # # 6. Retrieve and verify transformed image
        detail_url = reverse(
            "transformed_image_detail", kwargs={"pk": transformed_image_id}
        )

        response = self.client.get(detail_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        transformed_file_name = f"{source_image.file_name}_{task_id}.{response.data['metadata']['format'].lower()}"
        self.assertEqual(
            response.data["file_name"],
            transformed_file_name,
        )
        self.assertEqual(response.data["description"], self.image_description)

        # 7. List transformed images
        list_url = reverse("transformed_image_list")
        response = self.client.get(list_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Should have exactly one transformed image
        results = response.data["results"]
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["id"], transformed_image_id)
