"""
Shared test utilities for the image processing service tests.
"""

from io import BytesIO

from django.core.files.uploadedfile import SimpleUploadedFile
from PIL import Image


def create_test_image_file(filename="test.jpg", format="JPEG", size=(100, 100)):
    """
    Create a test image file with specified dimensions.

    Args:
        filename (str): The filename for the test image
        format (str): The image format (JPEG, PNG, etc.)
        size (tuple): The image dimensions as (width, height)

    Returns:
        SimpleUploadedFile: A test image file ready for upload
    """
    image = Image.new("RGB", size, color="red")
    image_io = BytesIO()
    image.save(image_io, format=format)
    image_io.seek(0)

    return SimpleUploadedFile(
        filename, image_io.getvalue(), content_type=f"image/{format.lower()}"
    )
