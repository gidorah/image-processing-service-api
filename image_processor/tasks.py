import logging

from celery import shared_task
from PIL import Image

from api.models import SourceImage, TransformationTask, TransformedImage

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

    task: TransformationTask = TransformationTask.objects.get(pk=task_id)

    if not task.transformations:
        raise Exception("No transformations found")  # TODO: Add custom exception

    logger.info(f"Applying transformations for task {task.id}")

    original_image = task.original_image

    image_file = task.original_image.file
    image = Image.open(image_file)

    for transformation in task.transformations:
        # TODO: Apply transformation
        logger.info(f"Applying transformation {transformation}")
        pass


def crop(image, x, y, width, height):
    """
    Crop an image.
    """
    box = (x, y, x + width, y + height)
    transformed_image = image.crop(box)
    return transformed_image


def resize(image_file, width, height):
    """
    Resize an image.
    """
    pass


def rotate(image_file, degrees):
    """
    Rotate an image.
    """
    pass


@shared_task
def watermark(image_file, watermark_file):
    """
    Watermark an image.
    """
    pass


@shared_task
def flip(image_file):
    """
    Flip an image.
    """
    pass


@shared_task
def mirror(image_file):
    """
    Mirror an image.
    """
    pass


@shared_task
def change_format(image_file, format):
    """
    Change the format of an image.
    """
    pass


@shared_task
def apply_filter(image_file, filter):
    """
    Apply a filter to an image.
    """
    pass
