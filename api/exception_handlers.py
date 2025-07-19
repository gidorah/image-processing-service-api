from rest_framework import status
from rest_framework.exceptions import ValidationError
from rest_framework.views import exception_handler


def custom_exception_handler(exc, context):
    """
    Convert "already registered" validation errors into 409 Conflict
    (or leave everything else untouched).
    """
    response = exception_handler(exc, context)

    # Only post-process DRF ValidationError responses
    if isinstance(exc, ValidationError) and response is not None:
        # Flatten the error messages and look for our duplicate-email text
        flat_messages = " ".join(
            " ".join(v if isinstance(v, list) else [v]) for v in response.data.values()
        ).lower()

        if "already registered" in flat_messages:
            response.status_code = status.HTTP_409_CONFLICT

    return response
