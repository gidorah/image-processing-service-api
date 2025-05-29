import hashlib
import json
import logging

from django.core.cache import cache

from utils.exceptions import MetadataExtractionError

logger = logging.getLogger(__name__)


def extract_metadata(image) -> dict:
    """
    Extract metadata from an image.
    """
    try:
        required_attrs = {
            "format": image.format,
            "mode": image.mode,
            "width": image.width,
            "height": image.height,
        }
        missing_attrs = [attr for attr, value in required_attrs.items() if not value]
        if missing_attrs:
            logger.error(
                f"Missing image metadata detected: {', '.join(missing_attrs)} - values: {image.format}, {image.mode}, {image.width}, {image.height}"
            )
            raise MetadataExtractionError(
                f"Missing image metadata: {', '.join(missing_attrs)}"
            )

        metadata = {}
        metadata["format"] = image.format
        metadata["format_description"] = image.format_description
        metadata["mode"] = image.mode
        metadata["width"] = image.width
        metadata["height"] = image.height
        # metadata["size"] = image_file.size
    except Exception as e:
        logger.error(f"Caught exception in extract_metadata: {type(e).__name__}: {e}")
        raise MetadataExtractionError(str(e))
    return metadata


def generate_transformation_cache_key(source_image_id, transformations, image_format):
    """
    Generate a cache key for the transformations that
    will be used to store and retrieve the transformed image
    for duplicate transformation requests.
    """

    try:
        transformations_str = json.dumps(transformations, sort_keys=True)
    except TypeError as e:
        logger.error(f"Error serializing transformations: {transformations} - {e}")
        return None  # Cannot generate a cache key

    format_str = image_format.lower() if image_format else "None"

    # Combine the source image ID, transformations, and format into a single string
    # to create a unique cache key
    key_data = f"{source_image_id}_{transformations_str}_{format_str}"

    # Use a hash function to generate a fixed-length cache key
    cache_key = hashlib.sha256(key_data.encode("utf-8")).hexdigest()
    logger.debug(f"Generated cache key: {cache_key}")
    return cache_key


def get_transformed_image_id_from_cache(source_image_id, transformations, image_format):
    """
    Get the transformed image ID from the cache using the cache key.
    """
    cache_key = generate_transformation_cache_key(
        source_image_id, transformations, image_format
    )
    if cache_key:
        transformed_image_id = cache.get(cache_key)
        if transformed_image_id:
            logger.debug(
                f"Transformed image ID {transformed_image_id} found in cache for key {cache_key}"
            )
            return transformed_image_id
        else:
            logger.debug(f"No transformed image ID found in cache for key {cache_key}")
    logger.error(f"Cache key generation failed for source_image_id: {source_image_id}")
    return None


def set_transformed_image_id_to_cache(
    source_image_id, transformations, image_format, transformed_image_id
):
    """
    Set the transformed image ID to the cache using the cache key.
    """
    cache_key = generate_transformation_cache_key(
        source_image_id, transformations, image_format
    )
    if not cache_key:
        logger.error(
            f"Cache key generation failed for source_image_id: {source_image_id}, transformations: {transformations}, image_format: {image_format}"
        )
        return

    try:
        cache.set(cache_key, transformed_image_id)
        logger.info(
            f"Transformed image ID {transformed_image_id} set in cache for key {cache_key}"
        )
    except Exception as e:
        logger.error(f"Error setting transformed image ID to cache: {e}")
