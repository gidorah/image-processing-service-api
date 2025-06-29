import logging
import os
import uuid

from botocore.exceptions import BotoCoreError, ClientError
from django.contrib.auth.models import AbstractUser
from django.db import models

from api.exceptions import StorageUploadFailed

logger = logging.getLogger(__name__)


class TaskStatus(models.TextChoices):
    """
    Task status choices to store the status of the transformation task
    """

    PENDING = "PENDING"
    IN_PROGRESS = "IN_PROGRESS"
    SUCCESS = "SUCCESS"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"


class User(AbstractUser):
    """
    Custom user model to store user information
    and extend the default Django user model
    to upcoming authentication requirements
    """

    email = models.EmailField(
        unique=True, null=False, blank=False, verbose_name="email address"
    )

    def __str__(self) -> str:
        return self.username


def unique_image_path(instance, filename):
    """
    Custom image path to avoid duplicate image names
    Because when we upload the same image twice,
    the second upload will overwrite the first one on
    the object storage
    """

    # Extract the file extension from the original filename
    ext = filename.split(".")[-1]

    # Generate a unique filename using UUID
    unique_filename = f"{uuid.uuid4()}.{ext}"

    # Return the full path (relative to storage root)
    return os.path.join("images", unique_filename)


class BaseImage(models.Model):
    """
    Base image model to create SourceImage and TransformedImage models
    """

    file = models.ImageField(upload_to=unique_image_path)  # Image file
    file_name = models.CharField(
        max_length=255
    )  # Original file name | for display purposes only
    description = models.TextField()  # User provided description
    metadata = models.JSONField(blank=True, null=True)  # Metadata about the image
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    owner = models.ForeignKey(User, on_delete=models.CASCADE)

    def save(self, *args, **kwargs):
        # Set name if not provided
        if not self.file_name and self.file:
            self.file_name = os.path.basename(self.file.name).split(".")[0]

        try:
            super().save(*args, **kwargs)  # S3 upload happens here
        except (ClientError, BotoCoreError) as e:
            logger.error(
                f"S3 Upload Error for file {getattr(self.file, 'name', 'N/A')}: {e}",
                exc_info=True,
            )
            raise StorageUploadFailed(
                detail=f"Failed to upload {self.file.name} to S3. "
                "Please try again later."
            ) from e

    def __str__(self) -> str:
        return f"{self.owner} - {self.file_name} : {self.description}"

    class Meta:
        abstract = True


class SourceImage(BaseImage):
    """
    Image model to store both original images
    """

    pass


class TransformedImage(BaseImage):
    """
    Image model to store transformed images
    """

    source_image = models.ForeignKey(
        SourceImage, on_delete=models.CASCADE, null=False
    )  # Original image
    transformation_task = models.ForeignKey(
        "TransformationTask", on_delete=models.CASCADE, null=False
    )  # Task that transformed the image


class TransformationTask(models.Model):
    """
    Transformation task model to store the status of the transformation task
    which will be processed by the worker
    """

    owner = models.ForeignKey(
        User, on_delete=models.CASCADE
    )  # User who requested the transformation
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    original_image = models.ForeignKey(
        SourceImage, on_delete=models.CASCADE
    )  # Original image
    result_image = models.ForeignKey(
        TransformedImage,
        on_delete=models.SET_NULL,
        null=True,
    )  # Transformed image
    status = models.CharField(
        max_length=20, default=TaskStatus.PENDING, choices=TaskStatus.choices
    )  # Status of the task (PENDING, IN_PROGRESS, SUCCESS, FAILED, CANCELLED)
    transformations = models.JSONField()  # List of transformations to be applied
    format = models.CharField(
        max_length=10, null=True, blank=True
    )  # Format of the transformed image
    error_message = models.TextField(
        null=True, blank=True
    )  # Error message if the transformation fails

    def __str__(self) -> str:
        return f"{self.original_image.file_name} - {self.status}"
