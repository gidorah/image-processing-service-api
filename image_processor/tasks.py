import io
import logging

from celery import shared_task
from django.core.files import File
from PIL import Image

from api.exceptions import (
    NoTransformationsDefined,
    OriginalImageNotFound,
    TaskNotFound,
)
from api.models import SourceImage, TaskStatus, TransformationTask, TransformedImage
from utils.utils import extract_metadata

logger = logging.getLogger(__name__)


@shared_task
def apply_transformations(task_id):
    """
    Receives the task id and applies the transformations
    according to the tranformations list by list order.

    Multiple transformations will be applied in serial fashion.
    Because seperating the transformations into different
    tasks will increase the image read/write and
    communication costs.
    """

    try:
        task: TransformationTask = TransformationTask.objects.get(pk=task_id)

        if not task:
            raise TaskNotFound()

        task.status = TaskStatus.IN_PROGRESS
        task.save()

        if not task.transformations:
            raise NoTransformationsDefined()

        logger.info(f"Applying transformations for task {task.id}")

        original_image = task.original_image

        if not original_image:
            raise OriginalImageNotFound()

        image_file = original_image.file
        image = Image.open(image_file)

        image_format = original_image.metadata.get("format")

        # If the format is not defined, use the original image format
        # as the default format. When saving the image, the format
        # will be changed to the format specified in the task.
        # Also remove the "change_format" transformation from the task
        # because it's not a transformation function.
        if "change_format" in task.transformations:
            image_format = task.transformations["change_format"].get("format")
            task.transformations.pop("change_format")

        for transformation_key, transformation in task.transformations.items():
            logger.info(f"Applying transformation {transformation_key}")
            image = TRANSFORMATION_MAP[transformation_key](image, **transformation)

        # Ensure the PIL image is in RGB mode (if saving as JPEG)
        if image.mode == "RGBA":
            image = image.convert("RGB")

        # Create a BytesIO buffer to temporarily store the image
        image_buffer = io.BytesIO()

        # Save the PIL image to the buffer with the specified format
        image.save(image_buffer, format=image_format)

        # Set the format of the image because:
        # https://pillow.readthedocs.io/en/stable/reference/Image.html#PIL.Image.Image.format
        # We need to set it for metadata extraction
        image.format = image_format

        # Reset buffer position to the beginning
        image_buffer.seek(0)

        file_name = f"{original_image.file_name}_{task.id}.{image_format.lower()}"

        # Create a Django File object from the buffer
        django_file = File(image_buffer, name=file_name)

        # Create and save the BaseImage instance
        result_image = TransformedImage.objects.create(
            owner=task.owner,
            file=django_file,
            file_name=file_name,
            description=original_image.description,
            source_image=original_image,
            transformation_task=task,
            metadata=extract_metadata(image=image),
        )
        result_image.save()
        # Close the buffer to free memory
        image_buffer.close()

        task.result_image = result_image

    except Exception as e:
        logger.error(f"Error while applying transformations: {e}")
        task.status = TaskStatus.FAILED
        task.save()
        raise e

    task.status = TaskStatus.SUCCESS
    task.save()


def crop(image: Image, x, y, width, height) -> Image:
    """
    Crop an image.
    """
    box = (x, y, x + width, y + height)
    return image.crop(box)


def resize(image: Image, width, height) -> Image:
    """
    Resize an image.
    """
    return image.resize((width, height))


def rotate(image: Image, degrees) -> Image:
    """
    Rotate an image.
    """
    return image.rotate(angle=degrees)


def watermark(image: Image, watermark_file) -> Image:
    """
    Watermark an image.
    """
    return image


def flip(image: Image) -> Image:
    """
    Flip an image.
    """
    pass


def mirror(image: Image) -> Image:
    """
    Mirror an image.
    """
    pass


def apply_filter(image: Image, *args, **kwargs) -> Image:
    """
    Apply a filter to an image.
    """
    return image


"""
The key is the name of the transformation function.
The value is the function itself.

This dictionary won't include the "change_format" transformation
because it's not a transformation function. And format change
is done in the apply_transformations function.
"""
TRANSFORMATION_MAP = {
    "crop": crop,
    "resize": resize,
    "rotate": rotate,
    "watermark": watermark,
    "flip": flip,
    "mirror": mirror,
    "apply_filter": apply_filter,
}
