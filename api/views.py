import logging

from django.http import JsonResponse
from django.shortcuts import render
from django.views.decorators.http import require_GET

# Create your views here.

# Update to use the 'api' logger that's configured in settings.py
logger = logging.getLogger('api')


@require_GET
def test_logging(request):
    """
    Test endpoint to verify logging with ELK stack.
    This endpoint generates logs at different levels.
    """
    logger.debug("This is a DEBUG level log message")
    logger.info("This is an INFO level log message")
    logger.warning("This is a WARNING level log message")
    logger.error("This is an ERROR level log message")
    logger.critical("This is a CRITICAL level log message")

    return JsonResponse(
        {
            "status": "success",
            "message": "Logs generated at all levels. Check your ELK stack to verify they were received.",
        }
    )
