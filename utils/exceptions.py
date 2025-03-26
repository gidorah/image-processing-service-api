from django.core.exceptions import ValidationError
from rest_framework import status


class MetadataExtractionFailed(ValidationError):
    status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
    default_detail = "Failed to extract metadata from image. Please try again later."
    default_code = "metadata_extraction_failed"
