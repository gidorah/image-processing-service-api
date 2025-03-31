from utils.exceptions import MetadataExtractionFailed


def extract_metadata(image) -> dict:
    """
    Extract metadata from an image.
    """
    try:
        metadata = {}
        metadata["format"] = image.format
        metadata["format_description"] = image.format_description
        metadata["mode"] = image.mode
        metadata["width"] = image.width
        metadata["height"] = image.height
        metadata["format"] = image.format
        # metadata["size"] = image_file.size
    except Exception as e:
        raise MetadataExtractionFailed(message=str(e))
    return metadata
