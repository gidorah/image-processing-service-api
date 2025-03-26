from rest_framework import status
from rest_framework.exceptions import APIException


class StorageUploadFailed(APIException):
    status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    default_detail = (
        "Failed to upload image to storage service. Please try again later."
    )
    default_code = "storage_upload_failed"
