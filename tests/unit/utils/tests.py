import logging
from unittest.mock import MagicMock, PropertyMock, patch

from django.test import TestCase

from utils.exceptions import MetadataExtractionFailed
from utils.utils import (
    extract_metadata,
    generate_transformation_cache_key,
    get_transformed_image_id_from_cache,
    set_transformed_image_id_to_cache,
)

logging.disable(logging.CRITICAL)


class TestExtractMetadata(TestCase):
    def test_extract_metadata_handles_corrupt_image(self):
        """Test that corrupt or invalid images are handled gracefully"""
        exception_str = "Corrupt image"

        mock_image = MagicMock()

        type(mock_image).format = PropertyMock(side_effect=Exception(exception_str))
        type(mock_image).mode = PropertyMock(side_effect=Exception(exception_str))
        type(mock_image).width = PropertyMock(side_effect=Exception(exception_str))
        type(mock_image).height = PropertyMock(side_effect=Exception(exception_str))

        with self.assertRaises(MetadataExtractionFailed) as context:
            extract_metadata(mock_image)
        self.assertIn(exception_str, str(context.exception))

    def test_extract_metadata_handles_missing_attributes(self):
        """Test that missing attributes are handled gracefully"""
        mock_image = MagicMock()
        mock_image.format = "JPEG"
        mock_image.mode = "RGB"
        mock_image.width = 800
        mock_image.height = None  # we missed height on purpose

        with self.assertRaises(MetadataExtractionFailed) as context:
            extract_metadata(mock_image)
        self.assertIn("Missing image metadata", str(context.exception))

    def test_extract_metadata_returns_required_fields(self):
        """Test that all required metadata fields for image processing are present"""
        mock_image = MagicMock()
        mock_image.format = "JPEG"
        mock_image.mode = "RGB"
        mock_image.width = 800
        mock_image.height = 600

        result = extract_metadata(mock_image)

        required_fields = {"format", "format_description", "mode", "width", "height"}
        self.assertTrue(all(field in result for field in required_fields))


class TestGenerateTransformationCacheKey(TestCase):
    def test_same_transformations_generate_same_key(self):
        """Test that identical transformations produce the same cache key"""
        source_id = "123"
        transformations = {
            "crop": {"x": 0, "y": 0, "width": 800, "height": 600},
            "rotate": 90,
        }
        format = "JPEG"

        key1 = generate_transformation_cache_key(source_id, transformations, format)
        key2 = generate_transformation_cache_key(source_id, transformations, format)

        self.assertEqual(key1, key2)

    def test_different_transformations_generate_different_keys(self):
        """Test that different transformations produce different cache keys"""
        source_id = "123"
        format = "JPEG"

        key1 = generate_transformation_cache_key(
            source_id,
            {"crop": {"x": 0, "y": 0, "width": 800, "height": 600}, "rotate": 90},
            format,
        )
        key2 = generate_transformation_cache_key(
            source_id,
            {
                "crop": {"x": 0, "y": 0, "width": 801, "height": 600},
                "rotate": 90,
            },  # we changed width on purpose
            format,
        )

        self.assertNotEqual(key1, key2)


class TestGetTransformedImageIdFromCache(TestCase):
    def test_retrieves_cached_transformation(self):
        """Test that we can retrieve a previously cached transformation"""
        source_id = "123"
        transformations = {
            "crop": {"x": 0, "y": 0, "width": 800, "height": 600},
            "rotate": 90,
        }
        format = "JPEG"
        expected_id = "456"

        # Mock the cache to return our expected ID
        with patch("django.core.cache.cache.get", return_value=expected_id):
            result = get_transformed_image_id_from_cache(
                source_id, transformations, format
            )

        self.assertEqual(result, expected_id)

    def test_handles_cache_miss_gracefully(self):
        """Test that cache misses return None without errors"""
        source_id = "123"
        transformations = {
            "crop": {"x": 0, "y": 0, "width": 800, "height": 600},
            "rotate": 90,
        }
        format = "JPEG"

        # Mock the cache to return None
        with patch("django.core.cache.cache.get", return_value=None):
            result = get_transformed_image_id_from_cache(
                source_id, transformations, format
            )

        self.assertIsNone(result)


class TestSetTransformedImageIdToCache(TestCase):
    def test_successfully_caches_transformation(self):
        """Test that transformed image IDs are properly cached"""
        source_id = "123"
        transformations = {
            "crop": {"x": 0, "y": 0, "width": 800, "height": 600},
            "rotate": 90,
        }
        format = "JPEG"
        transformed_id = "456"

        with patch("django.core.cache.cache.set") as mock_set:
            set_transformed_image_id_to_cache(
                source_id, transformations, format, transformed_id
            )
            mock_set.assert_called_once()

    def test_continues_on_cache_failure(self):
        """Test that cache failures don't break the application flow"""
        source_id = "123"
        transformations = {
            "crop": {"x": 0, "y": 0, "width": 800, "height": 600},
            "rotate": 90,
        }
        format = "JPEG"
        transformed_id = "456"

        # Even if cache.set fails, the function should complete
        with patch("django.core.cache.cache.set", side_effect=Exception("Cache error")):
            try:
                set_transformed_image_id_to_cache(
                    source_id, transformations, format, transformed_id
                )
            except Exception:
                self.fail("Cache failure should not raise an exception")
