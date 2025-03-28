import logging

from celery import shared_task
from PIL import Image

from api.models import SourceImage, TaskStatus, TransformationTask, TransformedImage

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
            raise Exception("Task not found")  # TODO: Add custom exception

        task.status = TaskStatus.IN_PROGRESS
        task.save()

        if not task.transformations:
            raise Exception("No transformations found")  # TODO: Add custom exception

        logger.info(f"Applying transformations for task {task.id}")

        original_image = task.original_image

        if not original_image:
            raise Exception("Original image not found")  # TODO: Add custom exception

        image_file = original_image.file
        image = Image.open(image_file)

        for transformation_key, transformation in task.transformations.items():
            logger.info(f"Applying transformation {transformation_key}")
            TRANSFORMATION_MAP[transformation_key](image, **transformation)

        # TODO: Add image assignment to the ImageField

        result_image = TransformedImage(
            owner=task.owner,
            file=image,
            file_name=original_image.file_name,
            description=original_image.description,
            metadata=original_image.metadata,
            source_image=original_image,
            transformation_task=task,
        )

        result_image.save()
        task.result_image = result_image

    except Exception as e:
        logger.error(f"Error while applying transformations: {e}")
        task.status = TaskStatus.FAILED
        task.save()
        raise e

    task.status = TaskStatus.SUCCESS
    task.save()


def crop(image, x, y, width, height):
    """
    Crop an image.
    """
    box = (x, y, x + width, y + height)
    image = image.crop(box)


def resize(image, width, height):
    """
    Resize an image.
    """
    pass


def rotate(image, degrees):
    """
    Rotate an image.
    """
    pass


def watermark(image, watermark_file):
    """
    Watermark an image.
    """
    pass


def flip(image):
    """
    Flip an image.
    """
    pass


def mirror(image):
    """
    Mirror an image.
    """
    pass


def change_format(image, format):
    """
    Change the format of an image.
    """
    pass


def apply_filter(image, *args, **kwargs):
    """
    Apply a filter to an image.
    """
    pass


TRANSFORMATION_MAP = {
    "crop": crop,
    "resize": resize,
    "rotate": rotate,
    "watermark": watermark,
    "flip": flip,
    "mirror": mirror,
    "change_format": change_format,
    "apply_filter": apply_filter,
}
