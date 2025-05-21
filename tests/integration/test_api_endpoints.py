from io import BytesIO

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import override_settings
from django.urls import reverse
from PIL import Image
from rest_framework import status
from rest_framework.test import APITestCase

from api.models import SourceImage, TransformationTask, TransformedImage

User = get_user_model()

# Override cache settings to avoid rate limiting
CACHE_OVERRIDE = {
    "CACHES": {
        "default": {
            "BACKEND": "django.core.cache.backends.dummy.DummyCache",
        }
    }
}


@override_settings(CACHES=CACHE_OVERRIDE["CACHES"])
class APIAuthenticationTests(APITestCase):
    def setUp(self):
        self.register_url = reverse("register")
        self.login_url = reverse("login")
        self.test_user_data = {"username": "testuser", "password": "testpass123"}

    def test_user_registration(self):
        """Test user registration endpoint"""
        response = self.client.post(self.register_url, self.test_user_data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(User.objects.filter(username="testuser").exists())

    def test_user_login(self):
        """Test user login endpoint"""
        # First create a user
        User.objects.create_user(**self.test_user_data)

        # Try to login
        response = self.client.post(self.login_url, self.test_user_data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("token", response.data)
        self.assertIn("access", response.data["token"])
        self.assertIn("refresh", response.data["token"])

    def test_wrong_credentials(self):
        """Test user login with wrong credentials"""

        # test wrong username
        response = self.client.post(
            self.login_url, {"username": "wrongusername", "password": "testpass123"}
        )
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

        # test wrong password
        response = self.client.post(
            self.login_url, {"username": "testuser", "password": "wrongpassword"}
        )
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_register_with_existing_username(self):
        """Test user registration with existing username"""
        user_data = {"username": "testuser_existing", "password": "testpass123"}
        response = self.client.post(self.register_url, user_data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        response = self.client.post(self.register_url, user_data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


@override_settings(CACHES=CACHE_OVERRIDE["CACHES"])
class APIImageUploadTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="testuser", password="testpass123"
        )
        self.client.force_authenticate(user=self.user)
        self.upload_url = reverse("source_image_upload")

        # Create a valid in-memory image file
        image = Image.new("RGB", (100, 100), color="red")
        buffer = BytesIO()
        image.save(buffer, format="JPEG")
        buffer.seek(0)
        self.test_image = SimpleUploadedFile(
            name="test_image.jpg", content=buffer.read(), content_type="image/jpeg"
        )

    def test_image_upload(self):
        """Test image upload endpoint"""
        data = {
            "file": self.test_image,
            "description": "Test image description",
            "file_name": "test_image",
        }
        response = self.client.post(self.upload_url, data, format="multipart")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(SourceImage.objects.filter(owner=self.user).exists())

    def test_upload_non_image_file(self):
        """Test uploading a non-image file (e.g., a text file)."""
        # Create a fake non-image file (e.g., a text file)
        non_image_content = b"This is not an image file."
        non_image_file = SimpleUploadedFile(
            name="test_document.txt",
            content=non_image_content,
            content_type="text/plain",
        )
        data = {
            "file": non_image_file,
            "description": "Test non-image file",
            "file_name": "test_document.txt",
        }
        response = self.client.post(self.upload_url, data, format="multipart")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_upload_unsupported_image_format(self):
        """Test uploading an image with an unsupported format (e.g., TIFF)."""
        # Create a fake TIFF image (Pillow can create TIFF in memory)
        image = Image.new("RGB", (60, 30), color="blue")
        buffer = BytesIO()
        image.save(buffer, format="TIFF")
        buffer.seek(0)
        unsupported_image_file = SimpleUploadedFile(
            name="test_image.tiff",
            content=buffer.read(),
            content_type="image/tiff",
        )
        data = {
            "file": unsupported_image_file,
            "description": "Test unsupported image format",
            "file_name": "test_image.tiff",
        }
        response = self.client.post(self.upload_url, data, format="multipart")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_upload_non_image_file(self):
        """Test uploading a non-image file (e.g., a text file)."""
        # Create a fake non-image file (e.g., a text file)
        non_image_content = b"This is not an image file."
        non_image_file = SimpleUploadedFile(
            name="test_document.txt",
            content=non_image_content,
            content_type="text/plain",
        )
        data = {
            "file": non_image_file,
            "description": "Test non-image file",
            "file_name": "test_document.txt",
        }
        response = self.client.post(self.upload_url, data, format="multipart")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_upload_unsupported_image_format(self):
        """Test uploading an image with an unsupported format (e.g., TIFF)."""
        # Create a fake TIFF image (Pillow can create TIFF in memory)
        image = Image.new("RGB", (60, 30), color="blue")
        buffer = BytesIO()
        image.save(buffer, format="TIFF")
        buffer.seek(0)
        unsupported_image_file = SimpleUploadedFile(
            name="test_image.tiff",
            content=buffer.read(),
            content_type="image/tiff",
        )
        data = {
            "file": unsupported_image_file,
            "description": "Test unsupported image format",
            "file_name": "test_image.tiff",
        }
        response = self.client.post(self.upload_url, data, format="multipart")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


@override_settings(CACHES=CACHE_OVERRIDE["CACHES"])
class APITransformationTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="testuser", password="testpass123"
        )
        self.client.force_authenticate(user=self.user)

        # Create a valid in-memory image file for the source image
        image = Image.new(
            "RGB", (100, 100), color="green"
        )  # Changed color to differentiate
        buffer = BytesIO()
        image.save(buffer, format="JPEG")
        buffer.seek(0)
        self.source_image_file_content = (
            buffer.read()
        )  # Store content for re-use if needed

        self.source_image = SourceImage.objects.create(
            owner=self.user,
            file=SimpleUploadedFile(
                name="test_source_image.jpg",  # Changed name for clarity
                content=self.source_image_file_content,
                content_type="image/jpeg",
            ),
            file_name="test_source_image",
            description="Test source image for transformations",
            metadata={
                "format": "JPEG",
                "width": 100,
                "height": 100,
            },  # Manually set metadata
        )

        self.transform_url = reverse(
            "create_transformed_image", kwargs={"pk": self.source_image.pk}
        )

    def test_create_transformation_task(self):
        """Test transformation task creation"""
        data = {
            "transformations": [
                {"operation": "resize", "params": {"width": 50, "height": 50}},
                {"operation": "apply_filter", "params": {"grayscale": True}},
            ]
        }
        response = self.client.post(self.transform_url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(
            TransformationTask.objects.filter(original_image=self.source_image).exists()
        )

    def test_create_transformation_for_non_existent_image(self):
        """Test creating a transformation for a source image that does not exist."""
        non_existent_image_pk = 99999  # An ID that is unlikely to exist
        url = reverse("create_transformed_image", kwargs={"pk": non_existent_image_pk})
        data = {"transformations": [{"operation": "grayscale"}]}
        response = self.client.post(url, data, format="json")
        print(response.data)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_create_transformation_invalid_resize_dimensions(self):
        """Test creating a transformation with invalid resize dimensions."""
        invalid_dimensions_data = [
            [{"operation": "resize", "params": {"width": -100, "height": 100}}],
            [{"operation": "resize", "params": {"width": 100, "height": -100}}],
            [{"operation": "resize", "params": {"width": 0, "height": 100}}],
            [{"operation": "resize", "params": {"width": 100, "height": 0}}],
        ]
        for transformations_list in invalid_dimensions_data:
            with self.subTest(transformations=transformations_list):
                data = {"transformations": transformations_list}
                response = self.client.post(self.transform_url, data, format="json")
                self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_create_transformation_unrecognized_type(self):
        """Test creating a transformation with an unrecognized transformation type."""
        data = {
            "transformations": [
                {"operation": "unknown_transform", "params": {"value": 123}}
            ]
        }
        response = self.client.post(self.transform_url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_create_transformation_missing_resize_parameters(self):
        """Test creating a resize transformation with missing required parameters."""
        missing_params_data = [
            [{"operation": "resize", "params": {"width": 100}}],
            [{"operation": "resize", "params": {"height": 100}}],
            [{"operation": "resize", "params": {}}],
        ]
        for transformations in missing_params_data:
            with self.subTest(transformations=transformations):
                data = {"transformations": transformations}
                response = self.client.post(self.transform_url, data, format="json")
                self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


@override_settings(CACHES=CACHE_OVERRIDE["CACHES"])
class APIImageRetrievalTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="testuser", password="testpass123"
        )
        self.client.force_authenticate(user=self.user)

        # Create test images
        self.source_image = SourceImage.objects.create(
            owner=self.user,
            file=SimpleUploadedFile(
                name="test_image.jpg",
                content=b"fake image content",
                content_type="image/jpeg",
            ),
            file_name="test_image",
            description="Test image",
        )

        # Create a transformation task first
        self.transformation_task = TransformationTask.objects.create(
            owner=self.user,
            original_image=self.source_image,
            transformations={
                "resize": {"params": {"width": 800, "height": 600}},
                "apply_filter": {"params": {"grayscale": True}},
            },
            status="completed",
        )

        # Now create the transformed image with the task
        self.transformed_image = TransformedImage.objects.create(
            owner=self.user,
            source_image=self.source_image,
            transformation_task=self.transformation_task,
            file=SimpleUploadedFile(
                name="transformed_image.jpg",
                content=b"fake transformed image content",
                content_type="image/jpeg",
            ),
            file_name="transformed_image",
            description="Transformed test image",
        )

    def test_list_source_images(self):
        """Test listing source images with pagination"""
        url = reverse("source_image_list")
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("results", response.data)
        self.assertEqual(len(response.data["results"]), 1)

    def test_list_transformed_images(self):
        """Test listing transformed images with pagination"""
        url = reverse("transformed_image_list")
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("results", response.data)
        self.assertEqual(len(response.data["results"]), 1)

    def test_retrieve_source_image(self):
        """Test retrieving a specific source image"""
        url = reverse("source_image_detail", kwargs={"pk": self.source_image.pk})
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["file_name"], "test_image")

    def test_retrieve_transformed_image(self):
        """Test retrieving a specific transformed image"""
        url = reverse(
            "transformed_image_detail", kwargs={"pk": self.transformed_image.pk}
        )
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["file_name"], "transformed_image")


# We don't override cache in the tests because we want to test the throttling behavior by individually
# filling the throttle limit with anonymous users and then authenticated users
class APIThrottlingTests(APITestCase):
    def setUp(self):
        self.anon_throttle_limit = int(
            settings.REST_FRAMEWORK["DEFAULT_THROTTLE_RATES"]["anon"].split("/")[0]
        )
        self.user_throttle_limit = int(
            settings.REST_FRAMEWORK["DEFAULT_THROTTLE_RATES"]["user"].split("/")[0]
        )

        self.register_url = reverse("register")

    def test_anonymous_user_throttling(self):
        """Test throttling for anonymous users by registering multiple users"""

        # Clear dummy cache to avoid premature throttling
        cache.clear()

        # Fill the throttle limit by registering more users than the limit
        # Since throttling count is not always equal to the limit, we need to
        # register way more users than the limit
        # https://www.django-rest-framework.org/api-guide/throttling/#a-note-on-concurrency
        for _ in range(self.anon_throttle_limit):
            test_user_data = {
                "username": f"testuser{_}",
                "password": f"testpass{_}",
            }

            response = self.client.post(self.register_url, test_user_data)
            self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        # Try one more time to exceed the limit
        test_user_data = {
            "username": f"testuser_{self.anon_throttle_limit}",
            "password": f"{self.anon_throttle_limit}==testpass",
        }
        response = self.client.post(self.register_url, test_user_data)
        print(response.data)
        self.assertEqual(response.status_code, status.HTTP_429_TOO_MANY_REQUESTS)


@override_settings(CACHES=CACHE_OVERRIDE["CACHES"])
class APIPermissionTests(APITestCase):
    def setUp(self):
        # Create two users
        self.user1 = User.objects.create_user(username="user1", password="testpass123")
        self.user2 = User.objects.create_user(username="user2", password="testpass123")

        # Create resources for user1
        self.source_image1 = SourceImage.objects.create(
            owner=self.user1,
            file=SimpleUploadedFile(
                name="test_image1.jpg",
                content=b"fake image content",
                content_type="image/jpeg",
            ),
            file_name="test_image1",
            description="Test image 1 for user 1",
        )
        self.transformation_task1 = TransformationTask.objects.create(
            owner=self.user1,
            original_image=self.source_image1,
            transformations=[
                {"operation": "apply_filter", "params": {"grayscale": True}}
            ],
            status="completed",
        )
        self.transformed_image1 = TransformedImage.objects.create(
            owner=self.user1,
            source_image=self.source_image1,
            transformation_task=self.transformation_task1,
            file=SimpleUploadedFile(
                name="transformed_image1.jpg",
                content=b"fake transformed image content",
                content_type="image/jpeg",
            ),
            file_name="transformed_image1",
            description="Transformed test image 1 for user 1",
        )

        # Create resources for user2
        self.source_image2 = SourceImage.objects.create(
            owner=self.user2,
            file=SimpleUploadedFile(
                name="test_image2.jpg",
                content=b"fake image content",
                content_type="image/jpeg",
            ),
            file_name="test_image2",
            description="Test image 2 for user 2",
        )
        self.transformation_task2 = TransformationTask.objects.create(
            owner=self.user2,
            original_image=self.source_image2,
            transformations=[{"operation": "rotate", "params": {"angle": 90}}],
            status="completed",
        )
        self.transformed_image2 = TransformedImage.objects.create(
            owner=self.user2,
            source_image=self.source_image2,
            transformation_task=self.transformation_task2,
            file=SimpleUploadedFile(
                name="transformed_image2.jpg",
                content=b"fake transformed image content",
                content_type="image/jpeg",
            ),
            file_name="transformed_image2",
            description="Transformed test image 2 for user 2",
        )

    def test_user_cannot_list_other_user_source_images(self):
        """Test that a user cannot list source images of another user."""
        self.client.force_authenticate(user=self.user1)
        url = reverse("source_image_list")
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        print(response.data)
        # User1 should only see their own source image
        self.assertEqual(len(response.data["results"]), 1)
        self.assertEqual(response.data["results"][0]["id"], self.source_image1.id)

    def test_user_cannot_retrieve_other_user_source_image(self):
        """Test that a user cannot retrieve a specific source image of another user."""
        self.client.force_authenticate(user=self.user1)
        # User1 tries to access source_image2 (owned by user2)
        url = reverse("source_image_detail", kwargs={"pk": self.source_image2.pk})
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_user_cannot_list_other_user_transformed_images(self):
        """Test that a user cannot list transformed images of another user."""
        self.client.force_authenticate(user=self.user1)
        url = reverse("transformed_image_list")
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # User1 should only see their own transformed image
        self.assertEqual(len(response.data["results"]), 1)
        self.assertEqual(response.data["results"][0]["id"], self.transformed_image1.id)

    def test_user_cannot_retrieve_other_user_transformed_image(self):
        """Test that a user cannot retrieve a specific transformed image of another user."""
        self.client.force_authenticate(user=self.user1)
        # User1 tries to access transformed_image2 (owned by user2)
        url = reverse(
            "transformed_image_detail", kwargs={"pk": self.transformed_image2.pk}
        )
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)


@override_settings(CACHES=CACHE_OVERRIDE["CACHES"])
class APITransformationTaskViewSetTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="taskuser", password="testpass123"
        )
        self.client.force_authenticate(user=self.user)

        # Create a valid source image first
        image_content = BytesIO()
        Image.new("RGB", (100, 100), color="red").save(image_content, format="JPEG")
        image_content.seek(0)

        self.source_image = SourceImage.objects.create(
            owner=self.user,
            file=SimpleUploadedFile(
                name="test_source_for_task.jpg",
                content=image_content.read(),
                content_type="image/jpeg",
            ),
            file_name="test_source_for_task.jpg",
            description="Source image for task tests",
            metadata={"format": "JPEG", "width": 100, "height": 100},
        )

        # Create a couple of transformation tasks
        self.task1_transformations = [{"operation": "grayscale", "params": {}}]
        self.task1 = TransformationTask.objects.create(
            owner=self.user,
            original_image=self.source_image,
            transformations=self.task1_transformations,
            status="pending",
        )

        self.task2_transformations = [
            {"operation": "resize", "params": {"width": 50, "height": 50}}
        ]
        self.task2 = TransformationTask.objects.create(
            owner=self.user,
            original_image=self.source_image,
            transformations=self.task2_transformations,
            status="completed",
        )

    def test_list_transformation_tasks(self):
        """Test listing transformation tasks for the authenticated user."""
        url = reverse("task-list")
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["results"]), 2)

        task_ids_in_response = {task["id"] for task in response.data["results"]}
        self.assertIn(self.task1.id, task_ids_in_response)
        self.assertIn(self.task2.id, task_ids_in_response)

    def test_retrieve_transformation_task(self):
        """Test retrieving a specific transformation task."""
        url = reverse("task-detail", kwargs={"pk": self.task1.pk})
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["id"], self.task1.id)
        self.assertEqual(response.data["status"], "pending")
        # Ensure transformations are correctly serialized (JSON string to Python list/dict)
        self.assertEqual(response.data["transformations"], self.task1_transformations)

    def test_retrieve_non_existent_transformation_task(self):
        """Test retrieving a non-existent transformation task."""
        non_existent_pk = 99999
        url = reverse("task-detail", kwargs={"pk": non_existent_pk})
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
