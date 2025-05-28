from rest_framework import status
from rest_framework.exceptions import APIException


class StorageUploadFailed(APIException):
    status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    default_detail = (
        "Failed to upload image to storage service. Please try again later."
    )
    default_code = "storage_upload_failed"


class TaskNotFound(APIException):
    status_code = status.HTTP_404_NOT_FOUND
    default_detail = "The requested transformation task was not found."
    default_code = "task_not_found"


class NoTransformationsDefined(APIException):
    status_code = status.HTTP_400_BAD_REQUEST
    default_detail = "No transformations were defined for this task."
    default_code = "no_transformations_defined"


class InvalidTransformation(APIException):
    status_code = status.HTTP_400_BAD_REQUEST
    default_detail = "The transformation provided is invalid."
    default_code = "invalid_transformation"


class OriginalImageNotFound(APIException):
    status_code = status.HTTP_404_NOT_FOUND
    default_detail = "The original image for this task was not found."
    default_code = "original_image_not_found"


class TransformationFailed(APIException):
    """
    Exception raised when a transformation task fails.
    This could be due to various reasons, such as an invalid transformation
    or an issue with the image processing library.

    But we are so sure that our excellent code will not fail,
    it should be bad request if it fails. :)
    """

    status_code = status.HTTP_400_BAD_REQUEST
    default_detail = (
        "The transformation task failed. Please check the logs for more details."
    )
    default_code = "transformation_failed"


class FileSizeExceededError(APIException):
    """
    Exception raised when a file size exceeds the maximum allowed size.
    """

    status_code = status.HTTP_413_REQUEST_ENTITY_TOO_LARGE
    default_detail = "File size exceeds the maximum allowed size."
    default_code = "file_size_exceeded"
