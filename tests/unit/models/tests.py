import io
import os  # Added import
import shutil
import tempfile

from django.core.files import File
from django.db import IntegrityError
from django.test import TestCase, override_settings
from PIL import Image

from api.models import (
    SourceImage,
    TaskStatus,
    TransformationTask,
    TransformedImage,
    User,
)


def create_test_image(file_name="test_image.jpg", format="JPEG", width=800, height=600):
    """
    Creates a temporary image file for testing.
    """

    image = Image.new("RGB", (width, height), color=(255, 0, 0))

    image_buffer = io.BytesIO()

    # Save to buffer
    image.save(image_buffer, format=format)

    # Set format attribute
    image.format = format

    # Reset buffer position
    image_buffer.seek(0)

    # Return a Django File object
    return File(image_buffer, name=file_name)


# Create a temporary directory for media files during tests
TEMP_MEDIA_ROOT = tempfile.mkdtemp()

TEST_USERNAME = "testuser"
TEST_PASSWORD = "testpassword"
TEST_FILE_NAME = "test_image"
TEST_DESCRIPTION = "Test image description"
TEST_FORMAT = "JPEG"
TEST_METADATA = {"initial_meta": "data"}


@override_settings(
    MEDIA_ROOT=TEMP_MEDIA_ROOT,
    DEFAULT_FILE_STORAGE="django.core.files.storage.FileSystemStorage",
)
class SourceImageModelTest(TestCase):
    """
    Test case for the SourceImage model. Since this model
    is simplest child of the BaseImage model, we test it
    here. The TransformedImage model is tested in a separate
    test case.

    We are using a temporary directory for media files
    and overriding the default file storage to use
    FileSystemStorage since we are not testing S3 storage here.
    """

    @classmethod
    def setUpTestData(cls):
        """Set up non-modified objects used by all test methods."""
        cls.user = User.objects.create_user(
            username=TEST_USERNAME, password=TEST_PASSWORD
        )

    def setUp(self):
        """Set up objects that may be modified by test methods."""
        self.source_image = SourceImage.objects.create(
            owner=self.user,
            file=create_test_image(format=TEST_FORMAT),
            file_name=TEST_FILE_NAME,
            description=TEST_DESCRIPTION,
            metadata=TEST_METADATA,
        )

    def test_owner_assignment(self):
        """Test that the owner is correctly assigned."""
        self.assertEqual(self.source_image.owner, self.user)
        self.assertEqual(self.source_image.owner.username, TEST_USERNAME)

    def test_source_image_attributes(self):
        """Test the basic attributes of the SourceImage model (inherited from BaseImage)."""
        self.assertEqual(self.source_image.file_name, TEST_FILE_NAME)
        self.assertEqual(self.source_image.description, TEST_DESCRIPTION)
        self.assertTrue(self.source_image.file.name.startswith("images/"))
        self.assertTrue(self.source_image.file.name.endswith(".jpg"))
        self.assertGreater(self.source_image.file.size, 0)
        self.assertIsInstance(self.source_image.file, File)
        self.assertEqual(self.source_image.metadata, TEST_METADATA)

    def test_source_image_str(self):
        """Test the string representation of the SourceImage model."""
        expected_str = f"{TEST_USERNAME} - {TEST_FILE_NAME} : {TEST_DESCRIPTION}"
        self.assertEqual(str(self.source_image), expected_str)

    def test_save_generates_filename_if_missing(self):
        """
        Test that save() generates file_name from image data
        if file_name is not initially provided.
        """
        # Create a test image file object first
        test_file = create_test_image(file_name="another_test.png", format="PNG")

        # Create a SourceImage instance without providing file_name
        source_image_no_name = SourceImage(
            owner=self.user,
            file=test_file,
            description="Image without initial file_name",
        )
        # Manually call save to trigger the logic
        source_image_no_name.save()

        # Check that file_name is generated from the file's base name
        self.assertIsNotNone(source_image_no_name.file_name)
        # The generated name should be the base name without extension
        expected_file_name = os.path.splitext(os.path.basename(test_file.name))[0]
        self.assertEqual(source_image_no_name.file_name, expected_file_name)

    def test_unique_image_path(self):
        """Test that saving two images with the same original name results in unique paths."""
        file1 = create_test_image(file_name="duplicate_name.jpg", format="JPEG")
        file2 = create_test_image(file_name="duplicate_name.jpg", format="JPEG")

        image1 = SourceImage.objects.create(
            owner=self.user, file=file1, description="First duplicate"
        )
        image2 = SourceImage.objects.create(
            owner=self.user, file=file2, description="Second duplicate"
        )

        self.assertNotEqual(image1.file.name, image2.file.name)
        self.assertTrue(image1.file.name.startswith("images/"))
        self.assertTrue(image2.file.name.startswith("images/"))
        self.assertTrue(image1.file.name.endswith(".jpg"))
        self.assertTrue(image2.file.name.endswith(".jpg"))

    @classmethod
    def tearDownClass(cls):
        if os.path.exists(TEMP_MEDIA_ROOT):
            shutil.rmtree(TEMP_MEDIA_ROOT, ignore_errors=True)
        super().tearDownClass()


@override_settings(
    MEDIA_ROOT=TEMP_MEDIA_ROOT,
    DEFAULT_FILE_STORAGE="django.core.files.storage.FileSystemStorage",
)
class TransformedImageModelTest(TestCase):
    """
    Test case for the TransformedImage model. This model
    is a child of the BaseImage model and has additional
    fields for the transformation task and the source image.

    We are using a temporary directory for media files
    and overriding the default file storage to use
    FileSystemStorage since we are not testing S3 storage here.
    We are also using a mock transformation task for testing
    purposes.
    """

    @classmethod
    def setUpTestData(cls):
        """Set up non-modified objects used by all test methods."""
        cls.user = User.objects.create_user(
            username=TEST_USERNAME, password=TEST_PASSWORD
        )
        # Create a source image that will persist for all tests in this class
        cls.source_image = SourceImage.objects.create(
            owner=cls.user,
            file=create_test_image(file_name="source.jpg", format="JPEG"),
            file_name="source_" + TEST_FILE_NAME,
            description="Original " + TEST_DESCRIPTION,
        )
        # Create a task that will persist for all tests in this class
        cls.transformation_task = TransformationTask.objects.create(
            original_image=cls.source_image,
            owner=cls.user,
            format="PNG",  # Different format for transformed
            transformations=[
                {"operation": "resize", "params": {"width": 100, "height": 100}}
            ],
        )

    @classmethod
    def setUpTestData(cls):
        """Set up non-modified objects used by all test methods."""
        cls.user = User.objects.create_user(
            username=TEST_USERNAME, password=TEST_PASSWORD
        )
        # Create a source image that will persist for all tests in this class
        cls.source_image = SourceImage.objects.create(
            owner=cls.user,
            file=create_test_image(file_name="source.jpg", format="JPEG"),
            file_name="source_" + TEST_FILE_NAME,
            description="Original " + TEST_DESCRIPTION,
        )
        # Create a task that will persist for all tests in this class
        cls.transformation_task = TransformationTask.objects.create(
            original_image=cls.source_image,
            owner=cls.user,
            format="PNG",  # Different format for transformed
            transformations=[
                {"operation": "resize", "params": {"width": 100, "height": 100}}
            ],
        )

    def setUp(self):
        """Set up objects that may be modified by test methods."""
        # Create a transformed image for each test method
        self.transformed_image = TransformedImage.objects.create(
            owner=self.user,  # Still need owner for creation
            file=create_test_image(file_name="transformed.png", format="PNG"),
            file_name="transformed_"
            + TEST_FILE_NAME,  # Still need file_name for creation/str
            description="Transformed "
            + TEST_DESCRIPTION,  # Still need description for creation/str
            metadata={"task_id": self.transformation_task.id},
            transformation_task=self.transformation_task,
            source_image=self.source_image,
        )

    def test_transformed_image_specific_relations(self):
        """Test relationships specific to the TransformedImage model."""
        # Test relationships specific to TransformedImage
        self.assertEqual(
            self.transformed_image.transformation_task, self.transformation_task
        )
        self.assertEqual(self.transformed_image.source_image, self.source_image)

    def test_cascade_delete_on_source_image(self):
        """Test that TransformedImage is deleted when its SourceImage is deleted."""
        source_image_id = self.source_image.id
        transformed_image_id = self.transformed_image.id
        self.assertTrue(SourceImage.objects.filter(id=source_image_id).exists())
        self.assertTrue(
            TransformedImage.objects.filter(id=transformed_image_id).exists()
        )

        # Delete the source image
        SourceImage.objects.get(id=source_image_id).delete()

        # Verify the transformed image is also deleted
        self.assertFalse(SourceImage.objects.filter(id=source_image_id).exists())
        self.assertFalse(
            TransformedImage.objects.filter(id=transformed_image_id).exists()
        )

    def test_cascade_delete_on_transformation_task(self):
        """Test that TransformedImage is deleted when its TransformationTask is deleted."""
        task_id = self.transformation_task.id
        transformed_image_id = self.transformed_image.id
        self.assertTrue(TransformationTask.objects.filter(id=task_id).exists())
        self.assertTrue(
            TransformedImage.objects.filter(id=transformed_image_id).exists()
        )

        # Delete the transformation task
        TransformationTask.objects.get(id=task_id).delete()

        # Verify the transformed image is also deleted
        self.assertFalse(TransformationTask.objects.filter(id=task_id).exists())
        self.assertFalse(
            TransformedImage.objects.filter(id=transformed_image_id).exists()
        )

    def test_missing_source_image_raises_error(self):
        """Test that creating a TransformedImage without a source_image raises IntegrityError."""

        with self.assertRaises(IntegrityError):
            TransformedImage.objects.create(
                owner=self.user,
                file=create_test_image(format="GIF"),
                file_name="no_source",
                description="Missing source",
                transformation_task=self.transformation_task,
                # source_image is missing (should violate NOT NULL constraint)
            )

    def test_missing_transformation_task_raises_error(self):
        """Test that creating a TransformedImage without a transformation_task raises IntegrityError."""

        with self.assertRaises(IntegrityError):
            TransformedImage.objects.create(
                owner=self.user,
                file=create_test_image(format="TIFF"),
                file_name="no_task",
                description="Missing task",
                source_image=self.source_image,
                # transformation_task is missing (should violate NOT NULL constraint)
            )

    @classmethod
    def tearDownClass(cls):
        # Clean up the temporary media directory once after all tests in the class
        if os.path.exists(TEMP_MEDIA_ROOT):
            shutil.rmtree(TEMP_MEDIA_ROOT, ignore_errors=True)
        super().tearDownClass()


@override_settings(
    MEDIA_ROOT=TEMP_MEDIA_ROOT,
    DEFAULT_FILE_STORAGE="django.core.files.storage.FileSystemStorage",
)
class TransformationTaskModelTest(TestCase):
    """
    Test case for the TransformationTask model."
    """

    @classmethod
    def setUpTestData(cls):
        """
        Set up non-modified objects used by all test methods.
        """
        cls.user = User.objects.create_user(
            username=TEST_USERNAME, password=TEST_PASSWORD
        )
        # Create a source image that will persist for all tests in this class
        cls.source_image = SourceImage.objects.create(
            owner=cls.user,
            file=create_test_image(file_name="source.jpg", format="JPEG"),
            file_name="source_" + TEST_FILE_NAME,
            description="Original " + TEST_DESCRIPTION,
        )

    def setUp(self):
        """
        Set up objects that may be modified by test methods.
        """
        # Create a transformation task for each test method
        self.transformation_task = TransformationTask.objects.create(
            owner=self.user,
            original_image=self.source_image,
            format="PNG",
            transformations=[
                {"operation": "resize", "params": {"width": 100, "height": 100}}
            ],
        )

    def test_transformation_task_str(self):
        """
        Test the string representation of the TransformationTask model.
        """
        expected_str = f"source_{TEST_FILE_NAME} - PENDING"
        self.assertEqual(str(self.transformation_task), expected_str)

    def test_transformation_task_specific_relations(self):
        """
        Test relationships specific to the TransformationTask model.
        """
        # Test relationships specific to TransformationTask
        self.assertEqual(self.transformation_task.original_image, self.source_image)

    def test_transformation_task_status(self):
        """
        Test the status field of the TransformationTask model.
        """
        self.assertEqual(self.transformation_task.status, TaskStatus.PENDING)

    def test_transformation_task_transformations(self):
        """
        Test the transformations field of the TransformationTask model.
        """
        self.assertEqual(
            self.transformation_task.transformations,
            [{"operation": "resize", "params": {"width": 100, "height": 100}}],
        )

    def test_transformation_task_format(self):
        """
        Test the format field of the TransformationTask model.
        """
        self.assertEqual(self.transformation_task.format, "PNG")

    def test_transformation_task_error_message(self):
        """
        Test the error_message field of the TransformationTask model.
        """
        self.assertEqual(self.transformation_task.error_message, None)

        error_message = "Error message"
        # Set the error message
        self.transformation_task.error_message = error_message
        self.transformation_task.save()

        # Verify the error message is set
        self.assertEqual(self.transformation_task.error_message, error_message)

    def test_transformation_task_cascade_delete_on_original_image(self):
        """
        Test that TransformationTask is deleted when its SourceImage is deleted.
        """
        source_image_id = self.source_image.id
        task_id = self.transformation_task.id
        self.assertTrue(SourceImage.objects.filter(id=source_image_id).exists())
        self.assertTrue(TransformationTask.objects.filter(id=task_id).exists())

        # Delete the source image
        SourceImage.objects.get(id=source_image_id).delete()

        # Verify the transformation task is also deleted
        self.assertFalse(SourceImage.objects.filter(id=source_image_id).exists())
        self.assertFalse(TransformationTask.objects.filter(id=task_id).exists())

    def test_transformation_task_set_null_on_result_image_delete(self):
        """
        Test that TransformationTask result_image is set to null when
        its TransformedImage is deleted.
        """
        task_id = self.transformation_task.id
        self.assertTrue(TransformationTask.objects.filter(id=task_id).exists())

        # Create a transformed image for the task
        transformed_image = TransformedImage.objects.create(
            format="PNG",
            transformations=[
                {"operation": "resize", "params": {"width": 100, "height": 100}}
            ],
        )

    def test_transformation_task_str(self):
        """
        Test the string representation of the TransformationTask model.
        """
        expected_str = f"source_{TEST_FILE_NAME} - PENDING"
        self.assertEqual(str(self.transformation_task), expected_str)

    def test_transformation_task_specific_relations(self):
        """
        Test relationships specific to the TransformationTask model.
        """
        # Test relationships specific to TransformationTask
        self.assertEqual(self.transformation_task.original_image, self.source_image)

    def test_transformation_task_status(self):
        """
        Test the status field of the TransformationTask model.
        """
        self.assertEqual(self.transformation_task.status, TaskStatus.PENDING)

    def test_transformation_task_transformations(self):
        """
        Test the transformations field of the TransformationTask model.
        """
        self.assertEqual(
            self.transformation_task.transformations,
            [{"operation": "resize", "params": {"width": 100, "height": 100}}],
        )

    def test_transformation_task_format(self):
        """
        Test the format field of the TransformationTask model.
        """
        self.assertEqual(self.transformation_task.format, "PNG")

    def test_transformation_task_error_message(self):
        """
        Test the error_message field of the TransformationTask model.
        """
        self.assertEqual(self.transformation_task.error_message, None)

        error_message = "Error message"
        # Set the error message
        self.transformation_task.error_message = error_message
        self.transformation_task.save()

        # Verify the error message is set
        self.assertEqual(self.transformation_task.error_message, error_message)

    def test_transformation_task_cascade_delete_on_original_image(self):
        """
        Test that TransformationTask is deleted when its SourceImage is deleted.
        """
        source_image_id = self.source_image.id
        task_id = self.transformation_task.id
        self.assertTrue(SourceImage.objects.filter(id=source_image_id).exists())
        self.assertTrue(TransformationTask.objects.filter(id=task_id).exists())

        # Delete the source image
        SourceImage.objects.get(id=source_image_id).delete()

        # Verify the transformation task is also deleted
        self.assertFalse(SourceImage.objects.filter(id=source_image_id).exists())
        self.assertFalse(TransformationTask.objects.filter(id=task_id).exists())

    def test_transformation_task_set_null_on_result_image_delete(self):
        """
        Test that TransformationTask result_image is set to null when
        its TransformedImage is deleted.
        """
        task_id = self.transformation_task.id
        self.assertTrue(TransformationTask.objects.filter(id=task_id).exists())

        # Create a transformed image for the task
        transformed_image = TransformedImage.objects.create(
            owner=self.user,
            file=create_test_image(file_name="transformed.png", format="PNG"),
            file_name="transformed_" + TEST_FILE_NAME,
            description="Transformed " + TEST_DESCRIPTION,
            metadata={"task_id": task_id},
            transformation_task=self.transformation_task,
            source_image=self.source_image,
        )

        # Set the result image for the task
        self.transformation_task.result_image = transformed_image
        self.transformation_task.save()

        # Verify the result image is set
        self.assertTrue(
            TransformedImage.objects.filter(id=transformed_image.id).exists()
        )

        # Delete the transformed image
        TransformedImage.objects.get(
            id=self.transformation_task.result_image.id
        ).delete()

        # Refresh the transformation task
        self.transformation_task.refresh_from_db()

        # Verify the result image set to null but the transformation task is not deleted
        self.assertTrue(TransformationTask.objects.filter(id=task_id).exists())
        self.assertFalse(expr=self.transformation_task.result_image)

    @classmethod
    def tearDownClass(cls):
        if os.path.exists(TEMP_MEDIA_ROOT):
            shutil.rmtree(TEMP_MEDIA_ROOT, ignore_errors=True)
        super().tearDownClass()
