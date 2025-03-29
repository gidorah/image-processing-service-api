import io
import logging
import math

from celery import shared_task
from django.core.files import File

# Add ImageOps, ImageFilter, ImageDraw, ImageFont
from PIL import Image, ImageDraw, ImageFilter, ImageOps

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

        # If the format is not defined in transformations,
        # use the original image format
        image_format = task.format
        if image_format is None:
            image_format = original_image.metadata.get("format")

        for transformation in task.transformations:
            operation = transformation.get("operation")
            params = transformation.get("params", {})

            logger.info(f"Applying transformation {operation} with params {params}")
            image = TRANSFORMATION_MAP[operation](image, **params)

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


def watermark(image: Image, watermark_text: str) -> Image:
    """
    Applies a standard, semi-transparent, diagonal watermark text across the image center.

    Args:
        image: The base image to watermark.
        watermark_text: The text to use as a watermark.

    Returns:
        The watermarked image.
    """

    # make a blank image for the text, initialized to transparent text color
    txt = Image.new("RGBA", image.size, (255, 255, 255, 0))

    # get a font
    # fnt = ImageFont.truetype("Pillow/Tests/fonts/FreeMono.ttf", 40)
    # get a drawing context
    d = ImageDraw.Draw(txt)

    # get image size
    w, h = image.size

    # draw text in the center of the image
    d.text((w / 2, h / 2), watermark_text, fill=(255, 255, 255, 128))

    # rotate text 45 degrees
    txt = txt.rotate(45)

    watermarked_image = Image.alpha_composite(image, txt)

    return watermarked_image


def flip(image: Image) -> Image:
    """
    Flip an image vertically (top to bottom).
    """
    return ImageOps.flip(image)


def mirror(image: Image) -> Image:
    """
    Mirror an image horizontally (left to right).
    """
    return ImageOps.mirror(image)


def grayscale(image: Image) -> Image:
    """
    Convert an image to grayscale.
    """
    return image.convert("L")


def sepia(image: Image) -> Image:
    """
    Apply a sepia filter to an image using a standard conversion matrix.
    Ensures the image is in RGB mode before applying the filter.
    """
    if image.mode != "RGB":
        image = image.convert("RGB")

    # Standard sepia conversion matrix based on common formulas:
    # R' = R*0.393 + G*0.769 + B*0.189
    # G' = R*0.349 + G*0.686 + B*0.168
    # B' = R*0.272 + G*0.534 + B*0.131
    # Pillow expects a 12-element tuple for RGB->RGB conversion matrix.
    sepia_matrix = (
        0.393,
        0.769,
        0.189,
        0,
        0.349,
        0.686,
        0.168,
        0,
        0.272,
        0.534,
        0.131,
        0,
    )
    # Note: Pillow clamps values automatically if they exceed 255.
    return image.convert("RGB", sepia_matrix)


def blur(image: Image) -> Image:
    """
    Apply a blur filter to an image.
    """
    return image.filter(ImageFilter.BLUR)


# Define available filters from ImageFilter
AVAILABLE_FILTERS = {
    "BLUR": blur,
    "GRAYSCALE": grayscale,
    "SEPIA": sepia,
    # Add other filters as needed, e.g., GaussianBlur, UnsharpMask might need parameters
    # "GaussianBlur": ImageFilter.GaussianBlur, # Example: Needs radius parameter
}


def apply_filter(image: Image, *args, **kwargs) -> Image:
    """
    Apply a predefined filter to an image.

    Args:
        image: The image to apply the filter to.
        filter_name: The name of the filter (e.g., "BLUR", "SHARPEN").
                     Must be a key in AVAILABLE_FILTERS.

    Returns:
        The filtered image, or the original image if the filter name is invalid.
    """

    for filter_name, filter_params in kwargs.items():
        filter_to_apply = AVAILABLE_FILTERS.get(filter_name.upper())
        if filter_to_apply:
            logger.info(f"Applying filter: {filter_name}")
            image = filter_to_apply(image)
        else:
            logger.warning(f"Invalid filter name: {filter_name}. No filter applied.")
            raise ValueError(f"Invalid filter name: {filter_name}")

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
