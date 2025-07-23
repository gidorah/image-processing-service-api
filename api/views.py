import logging

from rest_framework import generics, permissions, serializers, status, viewsets
from rest_framework.decorators import api_view, permission_classes
from rest_framework.exceptions import APIException
from rest_framework.response import Response

from api.models import SourceImage, TransformationTask, TransformedImage
from api.permissions import IsOwner
from api.serializers import (
    SourceImageDetailSerializer,
    SourceImageListSerializer,
    TransformationTaskSerializer,
    TransformedImageDetailSerializer,
    TransformedImageListSerializer,
    UploadImageSerializer,
)
from api.pagination import ReverseCursorPagination
from image_processor.tasks import apply_transformations

logger = logging.getLogger(__name__)


class SourceImageListView(generics.ListAPIView):
    """
    API view for listing and source images.
    """

    serializer_class = SourceImageListSerializer
    permission_classes = [permissions.IsAuthenticated, IsOwner]

    def get_queryset(self):
        """
        Return only images owned by the current user.
        """
        return SourceImage.objects.filter(owner=self.request.user)


class SourceImageDetailView(generics.RetrieveAPIView):
    """
    API view for retrieving a source image.
    """

    serializer_class = SourceImageDetailSerializer
    permission_classes = [permissions.IsAuthenticated, IsOwner]

    def get_queryset(self):
        """
        Return only images owned by the current user.
        """
        return SourceImage.objects.filter(owner=self.request.user)


@api_view(["POST"])
@permission_classes([permissions.IsAuthenticated])
def upload_image(request) -> Response:
    """
    API view for uploading an image.
    """

    serializer = UploadImageSerializer(data=request.data)

    try:
        serializer.is_valid(raise_exception=True)
        serializer.save(owner=request.user)
        return Response(serializer.data, status=status.HTTP_201_CREATED)
    except APIException as e:
        return Response(e.detail, status=e.status_code)
    except serializers.ValidationError as e:
        return Response(e.detail, status=e.status_code)
    except Exception as e:
        logger.error(f"Unhandled exception in upload_image: {e}")
        raise e


class TransformedImageListView(generics.ListAPIView):
    """
    API view for listing and transformed images.
    """

    serializer_class = TransformedImageListSerializer
    permission_classes = [permissions.IsAuthenticated, IsOwner]

    def get_queryset(self):
        """
        Return only transformed images owned by the current user.
        """
        return TransformedImage.objects.filter(owner=self.request.user)


class TransformedImageDetailView(generics.RetrieveAPIView):
    """
    API view for retrieving a transformed image.
    """

    serializer_class = TransformedImageDetailSerializer
    permission_classes = [permissions.IsAuthenticated, IsOwner]

    def get_queryset(self):
        """
        Return only transformed images owned by the current user.
        """
        return TransformedImage.objects.filter(owner=self.request.user)


class TransformationTaskViewSet(viewsets.ReadOnlyModelViewSet):
    """
    API view for listing and retrieving transformation tasks.
    """

    serializer_class = TransformationTaskSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        """
        Return only transformation tasks owned by the current user.
        """
        return TransformationTask.objects.filter(owner=self.request.user)


@api_view(["POST"])
@permission_classes([permissions.IsAuthenticated])
def create_transformed_image(request, pk):
    """
    API view for creating a transformed image.

    Creates a new transformation task for the given image
    and passes to the task queue. Returns the task ID for
    task tracking.
    """

    # Check if the source image exists and belongs to the user
    try:
        SourceImage.objects.get(pk=pk, owner=request.user)
    except SourceImage.DoesNotExist:
        return Response(
            {"error": "Source image not found or not owned by user"},
            status=status.HTTP_404_NOT_FOUND,
        )

    # Pass context={'request': request, 'pk': pk} to make request and pk
    # available in serializer context
    serializer = TransformationTaskSerializer(
        data=request.data, context={"request": request, "pk": pk}
    )
    if not serializer.is_valid():
        # Validation errors are handled by returning the response
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    serializer.save()

    # Pass the task to the task queue
    apply_transformations.delay(serializer.instance.id)

    # Return data instead of validated_data to include the task id
    return Response(serializer.data, status=status.HTTP_201_CREATED)


class TransformationTaskListByImageView(generics.ListAPIView):
    """
    API view for listing transformation tasks for a specific image.
    """

    serializer_class = TransformationTaskSerializer
    permission_classes = [permissions.IsAuthenticated, IsOwner]
    pagination_class = ReverseCursorPagination

    def get_queryset(self):
        """
        Return only transformation tasks for the given image
        owned by the current user.
        """
        image_id = self.kwargs.get("pk")
        return TransformationTask.objects.filter(
            owner=self.request.user, original_image__id=image_id
        )
