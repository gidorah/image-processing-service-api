"""
Integration tests for Celery task queue functionality.

These tests verify that the Django application correctly integrates with Celery
for asynchronous task execution, particularly for image processing tasks.
Uses CELERY_TASK_ALWAYS_EAGER for synchronous testing.
"""

from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings

from api.models import SourceImage, TaskStatus, TransformationTask, TransformedImage
from image_processor.tasks import apply_transformations
from tests.utils import create_test_image_file

User = get_user_model()

CELERY_TEST_SETTINGS = {
    "CELERY_TASK_ALWAYS_EAGER": True,
    "CELERY_TASK_EAGER_PROPAGATES": False,
    "CELERY_BROKER_URL": "memory://",
    "CELERY_RESULT_BACKEND": "cache+memory://",
    "CACHES": {
        "default": {
            "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
        }
    },
    "DEFAULT_FILE_STORAGE": "django.core.files.storage.FileSystemStorage",
}


@override_settings(**CELERY_TEST_SETTINGS)
class CeleryTaskIntegrationTests(TestCase):
    """
    Test suite for Celery task integration.
    Ensures that Celery tasks can be properly enqueued, executed, and return results.
    """

    def setUp(self):
        """
        Set up test data for Celery task testing.
        """
        self.user = User.objects.create_user(
            username="testuser", password="testpass123"
        )

        # Create a source image for testing
        self.test_image_file = create_test_image_file(
            "test_source.jpg", size=(200, 200)
        )
        self.source_image = SourceImage.objects.create(
            owner=self.user,
            file=self.test_image_file,
            file_name="test_source",
            description="Test source image for Celery integration",
            metadata={"format": "JPEG", "width": 200, "height": 200},
        )

    def test_apply_transformations_task_execution(self):
        """
        Test that the apply_transformations task can be executed successfully.
        """
        # Create a transformation task
        transformation_task = TransformationTask.objects.create(
            original_image=self.source_image,
            owner=self.user,
            format="JPEG",
            transformations=[
                {"operation": "resize", "params": {"width": 100, "height": 100}}
            ],
        )

        # Execute the task
        result = apply_transformations.delay(transformation_task.id)

        # Verify task completed successfully
        self.assertTrue(result.successful())

        # Refresh the task from database
        transformation_task.refresh_from_db()

        # Verify task status is SUCCESS
        self.assertEqual(transformation_task.status, TaskStatus.SUCCESS)

        # Verify result image was created
        self.assertIsNotNone(transformation_task.result_image)
        self.assertTrue(
            TransformedImage.objects.filter(
                transformation_task=transformation_task
            ).exists()
        )

        # Clean up to avoid constraint issues during test teardown
        if transformation_task.result_image_id:
            try:
                result_image = TransformedImage.objects.get(
                    id=transformation_task.result_image_id
                )
                transformation_task.result_image = None
                transformation_task.save()
                result_image.delete()
            except TransformedImage.DoesNotExist:
                # Image already deleted, just clear the reference
                transformation_task.result_image = None
                transformation_task.save()

    def test_apply_transformations_multiple_operations(self):
        """
        Test that multiple transformations can be applied in sequence.
        """
        transformation_task = TransformationTask.objects.create(
            original_image=self.source_image,
            owner=self.user,
            format="JPEG",
            transformations=[
                {"operation": "resize", "params": {"width": 150, "height": 150}},
                {"operation": "rotate", "params": {"degrees": 90}},
                {"operation": "apply_filter", "params": {"grayscale": True}},
            ],
        )

        # Execute the task
        result = apply_transformations.delay(transformation_task.id)

        # Verify task completed successfully
        self.assertTrue(result.successful())

        # Refresh the task from database
        transformation_task.refresh_from_db()

        # Verify task status is SUCCESS
        self.assertEqual(transformation_task.status, TaskStatus.SUCCESS)

        # Verify result image was created
        self.assertIsNotNone(transformation_task.result_image)

        # Verify the transformed image has expected properties
        transformed_image = transformation_task.result_image
        self.assertEqual(transformed_image.owner, self.user)
        self.assertEqual(transformed_image.source_image, self.source_image)

        # Clean up to avoid constraint issues during test teardown
        if transformation_task.result_image_id:
            try:
                result_image = TransformedImage.objects.get(
                    id=transformation_task.result_image_id
                )
                transformation_task.result_image = None
                transformation_task.save()
                result_image.delete()
            except TransformedImage.DoesNotExist:
                # Image already deleted, just clear the reference
                transformation_task.result_image = None
                transformation_task.save()

    def test_apply_transformations_task_failure_handling(self):
        """
        Test that task failures are properly handled and recorded.
        """
        # Create a transformation task with invalid operation
        transformation_task = TransformationTask.objects.create(
            original_image=self.source_image,
            owner=self.user,
            format="JPEG",
            transformations=[{"operation": "invalid_operation", "params": {}}],
        )

        # Execute the task (should fail)
        result = apply_transformations.delay(transformation_task.id)

        # Verify task failed
        self.assertFalse(result.successful())

        # Refresh the task from database
        transformation_task.refresh_from_db()

        # Verify task status is FAILED
        self.assertEqual(transformation_task.status, TaskStatus.FAILED)

        # Verify error message is recorded
        self.assertIsNotNone(transformation_task.error_message)
        self.assertIn("invalid_operation", transformation_task.error_message)

    def test_apply_transformations_invalid_task_id(self):
        """
        Test that providing an invalid task ID raises appropriate exception.
        """
        invalid_task_id = 99999

        # Execute the task with invalid ID (should fail)
        result = apply_transformations.delay(invalid_task_id)

        # Verify task failed
        self.assertFalse(result.successful())

    def test_apply_transformations_missing_source_image(self):
        """
        Test that task fails gracefully when source image is missing.
        """
        # Create a transformation task
        transformation_task = TransformationTask.objects.create(
            original_image=self.source_image,
            owner=self.user,
            format="JPEG",
            transformations=[
                {"operation": "resize", "params": {"width": 100, "height": 100}}
            ],
        )

        # Delete the source image file to simulate missing file
        self.source_image.file.delete()

        # Execute the task (should fail)
        result = apply_transformations.delay(transformation_task.id)

        # Verify task failed
        self.assertFalse(result.successful())

        # Refresh the task from database
        transformation_task.refresh_from_db()

        # Verify task status is FAILED
        self.assertEqual(transformation_task.status, TaskStatus.FAILED)

    def test_apply_transformations_empty_transformations_list(self):
        """
        Test that task fails when no transformations are defined.
        """
        # Create a transformation task with empty transformations
        transformation_task = TransformationTask.objects.create(
            original_image=self.source_image,
            owner=self.user,
            format="JPEG",
            transformations=[],
        )

        # Execute the task (should fail)
        result = apply_transformations.delay(transformation_task.id)

        # Verify task failed
        self.assertFalse(result.successful())
        self.assertEqual(result.state, "FAILURE")

        # Refresh the task from database
        transformation_task.refresh_from_db()

        # Verify task status is FAILED
        self.assertEqual(transformation_task.status, TaskStatus.FAILED)

    def test_apply_transformations_invalid_parameters(self):
        """
        Test that task fails when transformation parameters are invalid.
        """
        transformation_task = TransformationTask.objects.create(
            original_image=self.source_image,
            owner=self.user,
            format="JPEG",
            transformations=[
                {
                    "operation": "resize",
                    "params": {
                        "width": -100,
                        "height": -100,
                    },  # Invalid negative dimensions
                }
            ],
        )

        # Execute the task (should fail)
        result = apply_transformations.delay(transformation_task.id)

        # Verify task failed
        self.assertFalse(result.successful())

        # Refresh the task from database
        transformation_task.refresh_from_db()

        # Verify task status is FAILED
        self.assertEqual(transformation_task.status, TaskStatus.FAILED)

    def test_task_status_progression(self):
        """
        Test that task status progresses correctly from
        PENDING to IN_PROGRESS to SUCCESS.
        """
        transformation_task = TransformationTask.objects.create(
            original_image=self.source_image,
            owner=self.user,
            format="JPEG",
            transformations=[
                {"operation": "resize", "params": {"width": 100, "height": 100}}
            ],
        )

        # Initial status should be PENDING
        self.assertEqual(transformation_task.status, TaskStatus.PENDING)

        # Execute the task
        result = apply_transformations.delay(transformation_task.id)

        # Verify task completed successfully
        self.assertTrue(result.successful())

        # Refresh the task from database
        transformation_task.refresh_from_db()

        # Final status should be SUCCESS
        self.assertEqual(transformation_task.status, TaskStatus.SUCCESS)

        # Clean up to avoid constraint issues during test teardown
        if transformation_task.result_image_id:
            try:
                result_image = TransformedImage.objects.get(
                    id=transformation_task.result_image_id
                )
                transformation_task.result_image = None
                transformation_task.save()
                result_image.delete()
            except TransformedImage.DoesNotExist:
                # Image already deleted, just clear the reference
                transformation_task.result_image = None
                transformation_task.save()

    @patch("image_processor.tasks.get_transformed_image_id_from_cache")
    def test_apply_transformations_cache_hit(self, mock_cache_get):
        """
        Test that cached results are used when available.
        """
        # Create a transformation task first
        transformation_task = TransformationTask.objects.create(
            original_image=self.source_image,
            owner=self.user,
            format="JPEG",
            transformations=[
                {"operation": "resize", "params": {"width": 100, "height": 100}}
            ],
        )

        # Create an existing transformed image that will be "cached"
        # Note: We create this without linking to the transformation_task initially
        # to avoid circular reference issues during cleanup
        existing_transformed_image = TransformedImage.objects.create(
            owner=self.user,
            file=create_test_image_file("cached_result.jpg"),
            file_name="cached_result",
            description="Cached transformation result",
            source_image=self.source_image,
            transformation_task=transformation_task,  # Link to the task
        )

        # Mock cache to return the existing transformed image ID
        mock_cache_get.return_value = existing_transformed_image.id

        # Execute the task
        result = apply_transformations.delay(transformation_task.id)

        # Verify task completed successfully
        self.assertTrue(result.successful())

        # Refresh the task from database
        transformation_task.refresh_from_db()

        # Verify task status is SUCCESS
        self.assertEqual(transformation_task.status, TaskStatus.SUCCESS)

        # Verify the cached image was used
        self.assertEqual(
            transformation_task.result_image_id, existing_transformed_image.id
        )

        # Verify cache was checked
        mock_cache_get.assert_called_once()

        # Clean up to avoid constraint issues
        # First clear the result_image reference, then delete the transformed image
        transformation_task.result_image = None
        transformation_task.save()
        existing_transformed_image.delete()

    def test_concurrent_task_execution(self):
        """
        Test that multiple tasks can be executed concurrently without conflicts.
        """
        tasks = []

        # Create multiple transformation tasks
        for i in range(3):
            transformation_task = TransformationTask.objects.create(
                original_image=self.source_image,
                owner=self.user,
                format="JPEG",
                transformations=[
                    {
                        "operation": "resize",
                        "params": {"width": 50 + i * 10, "height": 50 + i * 10},
                    }
                ],
            )
            tasks.append(transformation_task)

        # Execute all tasks
        results = []
        for task in tasks:
            result = apply_transformations.delay(task.id)
            results.append(result)

        # Verify all tasks completed successfully
        for result in results:
            self.assertTrue(result.successful())

        # Verify all tasks have SUCCESS status
        for task in tasks:
            task.refresh_from_db()
            self.assertEqual(task.status, TaskStatus.SUCCESS)
            self.assertIsNotNone(task.result_image)

        # Clean up to avoid constraint issues during test teardown
        for task in tasks:
            if task.result_image_id:
                try:
                    result_image = TransformedImage.objects.get(id=task.result_image_id)
                    task.result_image = None
                    task.save()
                    result_image.delete()
                except TransformedImage.DoesNotExist:
                    # Image already deleted, just clear the reference
                    task.result_image = None
                    task.save()


@override_settings(**CELERY_TEST_SETTINGS)
class CeleryConfigurationTests(TestCase):
    """
    Test suite for Celery configuration and setup.
    """

    def test_celery_app_configuration(self):
        """
        Test that Celery app is properly configured.
        """
        from image_processing_service.celery import app

        self.assertIsNotNone(app)
        self.assertEqual(app.main, "image_processing_service")

    def test_task_discovery(self):
        """
        Test that tasks are properly discovered by Celery.
        """
        from image_processing_service.celery import app

        # Verify that our task is registered
        registered_tasks = list(app.tasks.keys())
        self.assertIn("image_processor.tasks.apply_transformations", registered_tasks)

    def test_task_routing(self):
        """
        Test that tasks can be properly routed and executed.
        """
        # This test verifies that the task routing mechanism works
        # by attempting to get task info
        from celery import current_app  # noqa: F401

        task_name = "image_processor.tasks.apply_transformations"
        task = current_app.tasks.get(task_name)

        self.assertIsNotNone(task)
        self.assertEqual(task.name, task_name)
