"""
Middleware for the image processing service.
"""
import json
import logging
import time
import uuid
from typing import Callable

from django.http import HttpRequest, HttpResponse

from image_processing_service.elasticsearch_utils import elasticsearch_client

logger = logging.getLogger(__name__)


class RequestLoggingMiddleware:
    """
    Middleware to log requests to Elasticsearch.
    """

    def __init__(self, get_response: Callable[[HttpRequest], HttpResponse]):
        """
        Initialize the middleware.

        Args:
            get_response: The function to get the response.
        """
        self.get_response = get_response
        self.index_name = "image-processing-service-requests"

    def __call__(self, request: HttpRequest) -> HttpResponse:
        """
        Process the request and log it to Elasticsearch.

        Args:
            request: The request to process.

        Returns:
            HttpResponse: The response from the view.
        """
        # Generate a unique request ID
        request_id = str(uuid.uuid4())
        request.META["REQUEST_ID"] = request_id

        # Log request start
        start_time = time.time()
        
        # Process the request
        response = self.get_response(request)
        
        # Calculate request duration
        duration = time.time() - start_time
        
        # Prepare log data
        log_data = {
            "request_id": request_id,
            "method": request.method,
            "path": request.path,
            "status_code": response.status_code,
            "duration": duration,
            "user_id": request.user.id if hasattr(request, "user") and request.user.is_authenticated else None,
            "ip_address": self._get_client_ip(request),
            "user_agent": request.META.get("HTTP_USER_AGENT", ""),
            "query_params": dict(request.GET.items()),
            "timestamp": time.time(),
        }
        
        # Log to console
        logger.info(f"Request: {json.dumps(log_data)}")
        
        # Log to Elasticsearch
        elasticsearch_client.index_document(
            index_name=self.index_name,
            document=log_data,
            doc_id=request_id,
        )
        
        return response

    def _get_client_ip(self, request: HttpRequest) -> str:
        """
        Get the client IP address from the request.

        Args:
            request: The request to get the IP address from.

        Returns:
            str: The client IP address.
        """
        x_forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")
        if x_forwarded_for:
            ip = x_forwarded_for.split(",")[0]
        else:
            ip = request.META.get("REMOTE_ADDR")
        return ip
