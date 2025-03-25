import os
import uuid

from django.contrib.auth.models import AbstractUser
from django.db import models

from utils.utils import extract_metadata


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

    def __str__(self) -> str:
        return self.username

    pass


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
    url = models.URLField()  # Object storage URL
    metadata = models.JSONField(blank=True, null=True)  # Metadata about the image
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    owner = models.ForeignKey(User, on_delete=models.CASCADE)

    def save(self, *args, **kwargs):
        # Set name if not provided
        if not self.file_name and self.file:
            self.file_name = os.path.basename(self.file.name).split(".")[0]

        # Extract and set metadata
        if self.file:
            self.metadata = extract_metadata(image_file=self.file.file)
        super().save(*args, **kwargs)

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
    )  # Status of the transformation task (PENDING, IN_PROGRESS, SUCCESS, FAILED, CANCELLED)
    transformations = models.JSONField()  # List of transformations to be applied

    def __str__(self) -> str:
        return f"{self.original_image.file_name} - {self.status}"
