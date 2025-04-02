import io
import shutil
import tempfile

from django.core.files import File
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

    def setUp(self):
        print("TEMP_MEDIA_ROOT", TEMP_MEDIA_ROOT)
        self.user = User.objects.create_user(
            username=TEST_USERNAME, password=TEST_PASSWORD
        )

        self.source_image: SourceImage = SourceImage.objects.create(
            owner=self.user,
            file=create_test_image(format=TEST_FORMAT),
            file_name=TEST_FILE_NAME,
            description=TEST_DESCRIPTION,
        )

    def test_owner_assignment(self):
        self.assertEqual(self.source_image.owner.username, TEST_USERNAME)

    def test_source_image_creation(self):
        self.assertEqual(self.source_image.file_name, TEST_FILE_NAME)
        self.assertEqual(self.source_image.description, TEST_DESCRIPTION)
        self.assertTrue(self.source_image.file.name.startswith("images/"))
        self.assertTrue(self.source_image.file.name.endswith(".jpg"))
        self.assertTrue(self.source_image.file.size > 0)
        self.assertIsInstance(self.source_image.file, File)

    def test_source_image_str(self):
        self.assertEqual(
            str(self.source_image),
            f"{TEST_USERNAME} - {TEST_FILE_NAME} : {TEST_DESCRIPTION}",
        )

    def test_save_generates_filename_if_missing(self):
        """
        Test that save() generates file_name from image data
        if file_name is not initially provided.
        """
        # Create a new SourceImage without file_name
        source_image = SourceImage.objects.create(
            owner=self.user,
            file=create_test_image(file_name=TEST_FILE_NAME, format=TEST_FORMAT),
            description=TEST_DESCRIPTION,
        )

        # Check that file_name is generated
        self.assertTrue(source_image.file_name)
        self.assertEqual(source_image.file_name, TEST_FILE_NAME)

    def tearDown(self):
        # Clean up the temporary media directory
        shutil.rmtree(TEMP_MEDIA_ROOT, ignore_errors=True)
        return super().tearDown()


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

    def setUp(self):
        print("TEMP_MEDIA_ROOT", TEMP_MEDIA_ROOT)
        self.user = User.objects.create_user(
            username=TEST_USERNAME, password=TEST_PASSWORD
        )
        self.source_image = SourceImage.objects.create(
            owner=self.user,
            file=create_test_image(format=TEST_FORMAT),
            file_name=TEST_FILE_NAME,
            description=TEST_DESCRIPTION,
        )
        self.transformation_task = TransformationTask.objects.create(
            original_image=self.source_image,
            owner=self.user,
            format=TEST_FORMAT,
            transformations=[],
        )
        self.transformed_image: TransformedImage = TransformedImage.objects.create(
            owner=self.user,
            file=create_test_image(format=TEST_FORMAT),
            file_name=TEST_FILE_NAME,
            description=TEST_DESCRIPTION,
            transformation_task=self.transformation_task,
            source_image=self.source_image,
        )

    def test_transformed_image_creation(self):
        self.assertEqual(self.transformed_image.file_name, TEST_FILE_NAME)
        self.assertIsInstance(self.transformed_image.file, File)
        self.assertEqual(
            self.transformed_image.transformation_task, self.transformation_task
        )

    def tearDown(self):
        # Clean up the temporary media directory
        shutil.rmtree(TEMP_MEDIA_ROOT, ignore_errors=True)
        return super().tearDown()
