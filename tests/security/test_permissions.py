from django.urls import reverse
from rest_framework import status

from tests.security.base import SecurityTestBase
from api.models import SourceImage, TransformationTask


class PermissionTest(SecurityTestBase):
    """
    Test suite for permission testing - ensuring users can only access their own resources
    """

    def setUp(self):
        super().setUp()

        # Create test images for both users
        self.authenticate_user(self.user_a)
        self.user_a_image = self.create_test_source_image(
            self.user_a, "user_a_image.jpg"
        )

        self.authenticate_user(self.user_b)
        self.user_b_image = self.create_test_source_image(
            self.user_b, "user_b_image.jpg"
        )

        # Clear authentication
        self.clear_authentication()

    def test_user_can_only_see_own_images_in_list(self):
        """Test that users can only see their own images in the list endpoint"""
        # User A should only see their own images
        self.authenticate_user(self.user_a)
        response = self.client.get(reverse("source_image_list"))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        image_ids = [img["id"] for img in response.data["results"]]
        self.assertIn(self.user_a_image.id, image_ids)
        self.assertNotIn(self.user_b_image.id, image_ids)

        # User B should only see their own images
        self.authenticate_user(self.user_b)
        response = self.client.get(reverse("source_image_list"))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        image_ids = [img["id"] for img in response.data["results"]]
        self.assertIn(self.user_b_image.id, image_ids)
        self.assertNotIn(self.user_a_image.id, image_ids)

    def test_user_cannot_access_other_users_image_detail(self):
        """Test that users cannot access other users' image details"""
        # User B tries to access User A's image
        self.authenticate_user(self.user_b)
        response = self.client.get(
            reverse("source_image_detail", kwargs={"pk": self.user_a_image.pk})
        )

        # Should return 404 to avoid information leakage (not 403)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

        # User A tries to access User B's image
        self.authenticate_user(self.user_a)
        response = self.client.get(
            reverse("source_image_detail", kwargs={"pk": self.user_b_image.pk})
        )

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_user_can_access_own_image_detail(self):
        """Test that users can access their own image details"""
        # User A can access their own image
        self.authenticate_user(self.user_a)
        response = self.client.get(
            reverse("source_image_detail", kwargs={"pk": self.user_a_image.pk})
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["id"], self.user_a_image.id)

        # User B can access their own image
        self.authenticate_user(self.user_b)
        response = self.client.get(
            reverse("source_image_detail", kwargs={"pk": self.user_b_image.pk})
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["id"], self.user_b_image.id)

    def test_user_cannot_transform_other_users_image(self):
        """Test that users cannot create transformations for other users' images"""
        self.authenticate_user(self.user_b)

        transformation_data = {
            "transformations": [{"type": "resize", "width": 100, "height": 100}],
            "format": "JPEG",
        }

        response = self.client.post(
            reverse("create_transformed_image", kwargs={"pk": self.user_a_image.pk}),
            transformation_data,
            format="json",
        )

        # Should return 404 to avoid information leakage
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_user_can_transform_own_image(self):
        """Test that users can create transformations for their own images"""
        self.authenticate_user(self.user_a)

        transformation_data = {
            "transformations": [
                {"operation": "resize", "params": {"width": 100, "height": 100}}
            ],
            "format": "JPEG",
        }

        response = self.client.post(
            reverse("create_transformed_image", kwargs={"pk": self.user_a_image.pk}),
            transformation_data,
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_user_cannot_access_other_users_transformation_tasks(self):
        """Test that users cannot access other users' transformation tasks"""
        # Create a transformation task for user A
        self.authenticate_user(self.user_a)
        task = TransformationTask.objects.create(
            owner=self.user_a,
            original_image=self.user_a_image,
            transformations=[
                {"operation": "resize", "params": {"width": 100, "height": 100}}
            ],
            format="JPEG",
        )

        # User B tries to access User A's task
        self.authenticate_user(self.user_b)
        response = self.client.get(reverse("task-detail", kwargs={"pk": task.pk}))

        # Should return 404 to avoid information leakage
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_user_can_access_own_transformation_tasks(self):
        """Test that users can access their own transformation tasks"""
        self.authenticate_user(self.user_a)
        task = TransformationTask.objects.create(
            owner=self.user_a,
            original_image=self.user_a_image,
            transformations=[
                {"operation": "resize", "params": {"width": 100, "height": 100}}
            ],
            format="JPEG",
        )

        response = self.client.get(reverse("task-detail", kwargs={"pk": task.pk}))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["id"], task.id)

    def test_user_cannot_access_other_users_tasks_in_list(self):
        """Test that users only see their own tasks in the task list"""
        # Create tasks for both users
        self.authenticate_user(self.user_a)
        task_a = TransformationTask.objects.create(
            owner=self.user_a,
            original_image=self.user_a_image,
            transformations=[
                {"operation": "resize", "params": {"width": 100, "height": 100}}
            ],
            format="JPEG",
        )

        self.authenticate_user(self.user_b)
        task_b = TransformationTask.objects.create(
            owner=self.user_b,
            original_image=self.user_b_image,
            transformations=[
                {"operation": "resize", "params": {"width": 200, "height": 200}}
            ],
            format="PNG",
        )

        # User A should only see their own task
        self.authenticate_user(self.user_a)
        response = self.client.get(reverse("task-list"))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        task_ids = [task["id"] for task in response.data["results"]]
        self.assertIn(task_a.id, task_ids)
        self.assertNotIn(task_b.id, task_ids)

        # User B should only see their own task
        self.authenticate_user(self.user_b)
        response = self.client.get(reverse("task-list"))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        task_ids = [task["id"] for task in response.data["results"]]
        self.assertIn(task_b.id, task_ids)
        self.assertNotIn(task_a.id, task_ids)

    def test_admin_user_permissions(self):
        """Test admin user permissions (if different from regular users)"""
        # Create image for regular user
        self.authenticate_user(self.user_a)
        user_image = self.create_test_source_image(self.user_a, "admin_test.jpg")

        # Admin should not automatically see all users' images unless explicitly permitted
        self.authenticate_user(self.admin_user)
        response = self.client.get(reverse("source_image_list"))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # Admin should only see their own images, not all users' images
        # (unless your business logic specifically grants admins access to all images)
        image_ids = [img["id"] for img in response.data["results"]]
        self.assertNotIn(user_image.id, image_ids)

    def test_object_level_permission_bypassing_attempts(self):
        """Test attempts to bypass object-level permissions"""
        self.authenticate_user(self.user_b)

        # Try to access with various manipulation attempts
        bypass_attempts = [
            self.user_a_image.pk,  # Direct access
            f"{self.user_a_image.pk}",  # String version
            str(self.user_a_image.pk),  # Explicit string conversion
        ]

        for pk in bypass_attempts:
            with self.subTest(pk=pk):
                response = self.client.get(
                    reverse("source_image_detail", kwargs={"pk": pk})
                )
                self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_permission_with_invalid_object_ids(self):
        """Test permission handling with invalid object IDs"""
        self.authenticate_user(self.user_a)

        invalid_ids = [
            99999,  # Non-existent ID
            0,  # Zero ID (invalid for positive integer primary keys)
        ]

        for invalid_id in invalid_ids:
            with self.subTest(invalid_id=invalid_id):
                response = self.client.get(
                    reverse("source_image_detail", kwargs={"pk": invalid_id})
                )
                # Should return 404, not 500
                self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_permission_inheritance_in_related_objects(self):
        """Test that permission checks work correctly for related objects"""
        # Create a transformation task
        self.authenticate_user(self.user_a)
        task = TransformationTask.objects.create(
            owner=self.user_a,
            original_image=self.user_a_image,
            transformations=[
                {"operation": "resize", "params": {"width": 100, "height": 100}}
            ],
            format="JPEG",
        )

        # User B should not be able to access this task
        self.authenticate_user(self.user_b)
        response = self.client.get(reverse("task-detail", kwargs={"pk": task.pk}))
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_bulk_access_attempts(self):
        """Test bulk access attempts to other users' resources"""
        self.authenticate_user(self.user_b)

        # Try to access multiple images belonging to user A
        for i in range(5):
            response = self.client.get(
                reverse("source_image_detail", kwargs={"pk": self.user_a_image.pk})
            )
            self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_permission_with_deleted_user_objects(self):
        """Test permission handling when related user objects are in inconsistent state"""
        # This test ensures that permission checks don't break with orphaned objects
        self.authenticate_user(self.user_a)

        # Create an image and then simulate accessing it
        image = self.create_test_source_image(self.user_a, "test_delete.jpg")

        response = self.client.get(
            reverse("source_image_detail", kwargs={"pk": image.pk})
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_cross_user_data_leakage_prevention(self):
        """Test that no user data leaks across user boundaries"""
        # Create images with sensitive information in metadata
        self.authenticate_user(self.user_a)
        sensitive_image_a = SourceImage.objects.create(
            file=self.create_test_image_file("sensitive_a.jpg"),
            file_name="sensitive_document_a.jpg",
            description="Confidential user A data",
            metadata={"sensitive": "user_a_secret_data"},
            owner=self.user_a,
        )

        self.authenticate_user(self.user_b)
        sensitive_image_b = SourceImage.objects.create(
            file=self.create_test_image_file("sensitive_b.jpg"),
            file_name="sensitive_document_b.jpg",
            description="Confidential user B data",
            metadata={"sensitive": "user_b_secret_data"},
            owner=self.user_b,
        )

        # User A tries to access User B's sensitive data
        self.authenticate_user(self.user_a)
        response = self.client.get(
            reverse("source_image_detail", kwargs={"pk": sensitive_image_b.pk})
        )
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

        # User B tries to access User A's sensitive data
        self.authenticate_user(self.user_b)
        response = self.client.get(
            reverse("source_image_detail", kwargs={"pk": sensitive_image_a.pk})
        )
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_permission_bypass_via_http_methods(self):
        """Test that permission checks work across different HTTP methods"""
        methods_and_data = [
            ("GET", None),
            (
                "POST",
                {
                    "transformations": [
                        {"operation": "resize", "params": {"width": 100, "height": 100}}
                    ]
                },
            ),
            (
                "PUT",
                {
                    "transformations": [
                        {"operation": "resize", "params": {"width": 200, "height": 200}}
                    ]
                },
            ),
            (
                "PATCH",
                {"transformations": [{"operation": "rotate", "params": {"angle": 90}}]},
            ),
            ("DELETE", None),
        ]

        self.authenticate_user(self.user_b)

        for method, data in methods_and_data:
            with self.subTest(method=method):
                url = reverse(
                    "create_transformed_image", kwargs={"pk": self.user_a_image.pk}
                )

                if method == "GET":
                    response = self.client.get(url)
                elif method == "POST":
                    response = self.client.post(url, data, format="json")
                elif method == "PUT":
                    response = self.client.put(url, data, format="json")
                elif method == "PATCH":
                    response = self.client.patch(url, data, format="json")
                elif method == "DELETE":
                    response = self.client.delete(url)

                # All should be denied - either 404 (not found), 405 (method not allowed), or 400 (bad request)
                self.assertIn(
                    response.status_code,
                    [
                        status.HTTP_404_NOT_FOUND,
                        status.HTTP_405_METHOD_NOT_ALLOWED,
                        status.HTTP_403_FORBIDDEN,
                        status.HTTP_400_BAD_REQUEST,
                    ],
                )
