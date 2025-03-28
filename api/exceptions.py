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


class OriginalImageNotFound(APIException):
    status_code = status.HTTP_404_NOT_FOUND
    default_detail = "The original image for this task was not found."
    default_code = "original_image_not_found"
