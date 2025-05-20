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


@override_settings(CACHES=CACHE_OVERRIDE["CACHES"])
class APITransformationTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="testuser", password="testpass123"
        )
        self.client.force_authenticate(user=self.user)

        # Create a test source image
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

        self.transform_url = reverse(
            "create_transformed_image", kwargs={"pk": self.source_image.pk}
        )

    def test_create_transformation_task(self):
        """Test transformation task creation"""
        data = {
            "transformations": {
                "resize": {"width": 800, "height": 600},
                "grayscale": True,
            }
        }
        response = self.client.post(self.transform_url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(
            TransformationTask.objects.filter(original_image=self.source_image).exists()
        )


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
                "resize": {"width": 800, "height": 600},
                "grayscale": True,
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

    # @override_settings(CACHES=CACHE_OVERRIDE["CACHES"])
    def test_user_throttling(self):
        """Test throttling for authenticated users"""

        # Clear dummy cache to avoid premature throttling
        cache.clear()

        # First authenticate a user since we need to be authenticated to upload source images
        self.user = User.objects.create_user(
            username="authenticated_user", password="testpass123"
        )
        self.client.force_authenticate(user=self.user)

        # Test uploading source images
        url = reverse("source_image_list")
        for _ in range(self.user_throttle_limit):
            response = self.client.get(url)
            self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Try one more time to exceed the limit
        response = self.client.get(url)
        print(response.data)
        self.assertEqual(response.status_code, status.HTTP_429_TOO_MANY_REQUESTS)
