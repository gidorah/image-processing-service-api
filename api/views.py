import logging

from django.http import HttpResponse

logger = logging.getLogger(__name__)


# Create your views here.
def logging_test(request):
    # This will log a message to the console and to the file
    logger.info("This is an info message")
    return HttpResponse("Check the logs for the message")
