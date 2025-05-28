from django.test import TestCase
from PIL import Image, ImageDraw

from api.exceptions import InvalidTransformation
from image_processor.tasks import (
    TRANSFORMATION_MAP,
    apply_filter,
    blur,
    crop,
    flip,
    grayscale,
    mirror,
    resize,
    rotate,
    sepia,
    watermark,
)


class TestImageTransformations(TestCase):
    """Test suite for basic image transformation functions."""

    def setUp(self):
        """Create a test image for each test."""
        # Create a cross gradient image
        self.test_image = Image.new("RGBA", (100, 100))
        draw = ImageDraw.Draw(self.test_image)
        for x in range(100):
            # Create a gradient from red to blue
            color = (255, 0, int(x * 2.55))  # Gradually increase blue component
            draw.line([(x, 0), (x, 100)], fill=color)

    def test_crop_should_return_correct_size(self):
        """Test image cropping functionality."""
        # Test cropping a portion of the image
        cropped = crop(self.test_image, x=10, y=10, width=50, height=50)
        self.assertEqual(cropped.size, (50, 50))

    def test_crop_should_raise_value_error_if_invalid_dimensions(self):
        """Test image cropping functionality."""
        # Test cropping with invalid dimensions
        with self.assertRaises(ValueError):
            crop(self.test_image, x=90, y=90, width=50, height=50)

    def test_resize(self):
        """Test image resizing functionality."""
        # Test resizing to smaller dimensions
        resized = resize(self.test_image, width=50, height=50)
        self.assertEqual(resized.size, (50, 50))

        # Test resizing to larger dimensions
        resized = resize(self.test_image, width=200, height=200)
        self.assertEqual(resized.size, (200, 200))

    def test_rotate(self):
        """Test image rotation functionality."""
        # Test 90-degree rotation
        rotated = rotate(self.test_image, degrees=90)
        self.assertEqual(
            rotated.size, (100, 100)
        )  # Size should remain same for 90-degree rotation

        # Test 45-degree rotation (should expand canvas)
        rotated = rotate(self.test_image, degrees=45)
        self.assertGreaterEqual(rotated.size[0], 100)
        self.assertGreaterEqual(rotated.size[1], 100)

    def test_watermark_should_return_correct_size_and_mode(self):
        """Test watermark application functionality."""
        # Test watermark with text
        watermarked = watermark(self.test_image, watermark_text="Test")
        self.assertEqual(watermarked.size, self.test_image.size)
        self.assertEqual(watermarked.mode, "RGBA")  # Should be RGBA after watermark

    def test_watermark_should_raise_value_error_if_invalid_text(self):
        """Test watermark application functionality."""
        # Test watermark with empty text
        with self.assertRaises(ValueError):
            watermark(self.test_image, watermark_text="")

    def test_flip_should_return_correct_size_and_mode(self):
        """Test vertical flip functionality."""

        # test with a gradient image
        gradient_image = Image.new("RGB", (100, 100))
        draw = ImageDraw.Draw(gradient_image)
        for y in range(100):
            # Create a gradient from red to blue
            color = (255, 0, int(y * 2.55))  # Gradually increase blue component
            draw.line([(0, y), (100, y)], fill=color)

        flipped = flip(gradient_image)
        self.assertEqual(flipped.size, gradient_image.size)
        # Verify the image is actually flipped by comparing pixel values
        self.assertNotEqual(gradient_image.getpixel((0, 0)), flipped.getpixel((0, 0)))

    def test_mirror_should_return_correct_size_and_mode(self):
        """Test horizontal mirror functionality."""
        mirrored = mirror(self.test_image)
        self.assertEqual(mirrored.size, self.test_image.size)
        # Verify the image is actually mirrored by comparing pixel values
        self.assertNotEqual(self.test_image.getpixel((0, 0)), mirrored.getpixel((0, 0)))

    def test_grayscale_should_return_correct_size_and_mode(self):
        """Test grayscale conversion functionality."""
        grayscaled = grayscale(self.test_image)
        self.assertEqual(grayscaled.mode, "L")  # Should be grayscale mode
        self.assertEqual(grayscaled.size, self.test_image.size)

    def test_sepia_should_return_correct_size_and_mode(self):
        """Test sepia filter functionality."""
        sepia_image = sepia(self.test_image)
        self.assertEqual(sepia_image.mode, "RGB")  # Should remain in RGB mode
        self.assertEqual(sepia_image.size, self.test_image.size)

        # Test with RGBA image
        rgba_image = Image.new("RGBA", (100, 100), color="red")
        sepia_rgba = sepia(rgba_image)
        self.assertEqual(sepia_rgba.mode, "RGB")  # Should convert to RGB

    def test_blur_should_return_correct_size_and_mode(self):
        """Test blur filter functionality."""
        # Apply blur
        blurred = blur(self.test_image)

        # compare whole image and count the difference
        is_different = False
        for x in range(100):
            for y in range(100):
                if self.test_image.getpixel((x, y)) != blurred.getpixel((x, y)):
                    is_different = True
                    break

        self.assertTrue(is_different)

        # The blurred image should still maintain the same size
        self.assertEqual(blurred.size, self.test_image.size)

    def test_apply_filter_should_return_correct_size_and_mode(self):
        """Test filter application functionality."""
        # Test applying a valid filter
        filtered = apply_filter(self.test_image, blur=True)
        self.assertEqual(filtered.size, self.test_image.size)

        # Test applying multiple filters
        filtered = apply_filter(self.test_image, blur=True, grayscale=True)
        self.assertEqual(
            filtered.mode, "L"
        )  # Should be grayscale after grayscale filter

    def test_apply_filter_should_raise_value_error_if_invalid_filter(self):
        """Test filter application functionality."""
        # Test applying an invalid filter
        with self.assertRaises(InvalidTransformation):
            apply_filter(self.test_image, invalid_filter=True)


class TestTransformationMap(TestCase):
    """Test suite for transformation map configuration."""

    def test_transformation_map_contains_all_operations(self):
        """Test that all transformation operations are properly mapped."""
        expected_operations = {
            "crop",
            "resize",
            "rotate",
            "watermark",
            "flip",
            "mirror",
            "apply_filter",
        }
        self.assertEqual(set(TRANSFORMATION_MAP.keys()), expected_operations)

    def test_transformation_map_functions_are_callable(self):
        """Test that all mapped functions are actually callable."""
        for operation, func in TRANSFORMATION_MAP.items():
            self.assertTrue(callable(func), f"{operation} is not callable")
