from django.contrib.auth.models import AbstractUser
from django.db import models


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

    pass


class Image(models.Model):
    """
    Image model to store both original and transformed images
    """

    file_name = models.CharField(
        max_length=255
    )  # Original file name | for display purposes only
    description = models.TextField()  # User provided description
    url = models.URLField()  # Object storage URL
    metadata = models.JSONField()  # Metadata about the image
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    owner = models.ForeignKey(User, on_delete=models.CASCADE)
    original_image = models.ForeignKey(
        "Image", on_delete=models.CASCADE, null=True
    )  # If this image is a transformation, this field will point to the original image
    transformation_task = models.ForeignKey(
        "TransformationTask", on_delete=models.CASCADE, null=True
    )  # If this image is a transformation, this field will point to the transformation task

    def __str__(self):
        return f"{self.file_name} - {self.owner}: {self.description}"


class TransformationTask(models.Model):
    """
    Transformation task model to store the status of the transformation task
    which will be processed by the worker
    """

    image = models.ForeignKey(Image, on_delete=models.CASCADE)  # Original image
    user = models.ForeignKey(
        User, on_delete=models.CASCADE
    )  # User who requested the transformation
    status = models.CharField(
        max_length=20, default=TaskStatus.PENDING, choices=TaskStatus.choices
    )  # Status of the transformation task (PENDING, IN_PROGRESS, SUCCESS, FAILED, CANCELLED)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    transformations = models.JSONField()  # List of transformations to be applied
    result = models.ForeignKey(
        Image, on_delete=models.SET_NULL, null=True
    )  # Transformed image

    def __str__(self):
        return f"{self.image.file_name} - {self.status}"
