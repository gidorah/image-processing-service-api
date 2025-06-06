import io
import logging
from collections.abc import Callable

from celery import shared_task  # type: ignore
from django.core.files import File
from django.db.models.fields.files import ImageFieldFile

# Add ImageOps, ImageFilter, ImageDraw, ImageFont
from PIL import Image, ImageDraw, ImageFilter, ImageOps

from api.exceptions import (
    InvalidTransformation,
    NoTransformationsDefined,
    OriginalImageNotFound,
    TaskNotFound,
    TransformationFailed,
)
from api.models import SourceImage, TaskStatus, TransformationTask, TransformedImage
from utils.utils import (
    extract_metadata,
    get_transformed_image_id_from_cache,
    set_transformed_image_id_to_cache,
)

logger = logging.getLogger(__name__)

# Defining Callable type for transformation functions
# to catch potential type errors
TransformFunc = Callable[..., Image.Image | None]


def _get_task_and_set_in_progress(task_id) -> TransformationTask:
    """
    Gets task, validates, sets status to IN_PROGRESS.
    """

    # Check if task with given id exists
    try:
        task: TransformationTask = TransformationTask.objects.get(pk=task_id)
    except TransformationTask.DoesNotExist:
        logger.error(f"Task with id {task_id} not found.")
        raise TaskNotFound(f"Task with id {task_id} not found.")

    if not task.transformations:
        logger.error(f"No transformations were defined for task: {task_id}.")
        task.status = TaskStatus.FAILED
        task.error_message = "No transformations were defined for task."
        task.save()
        raise NoTransformationsDefined()

    # Since task and transformations are valid, set status to IN_PROGRESS
    task.status = TaskStatus.IN_PROGRESS
    task.save()

    return task


def _load_image_and_determine_format(
    task: TransformationTask,
) -> tuple[Image.Image, str, SourceImage]:
    """
    Loads image, determines format.
    """

    source_image_instance = task.original_image

    if not source_image_instance:
        logger.error(f"Original image for task: {task.id} not found.")
        raise OriginalImageNotFound()

    image_file: ImageFieldFile = source_image_instance.file

    processed_image: Image.Image = Image.open(image_file)

    # Determine format
    image_format = task.format
    if image_format is None:
        logger.info(
            f"Format not found for task: {task.id}. Trying to get from metadata."
        )

        if source_image_instance.metadata is None:
            logger.error(f"Metadata not found for task: {task.id}. Format not found.")
            raise OriginalImageNotFound(
                detail=f"Metadata not found for task: {task.id}. Format not found."
            )

        image_format = source_image_instance.metadata.get("format")

        # If format is still None, would fail later
        if not image_format:
            logger.error(f"Format not found for task: {task.id}.")
            raise OriginalImageNotFound(
                detail="Format not found in metadata for task: {task_id}."
            )

    return (
        processed_image,
        image_format,
        source_image_instance,
    )


def _apply_processing_steps(
    processed_image: Image.Image | None,
    task: TransformationTask,
    image_format: str,
) -> Image.Image | None:
    """
    Applies transformations and final color mode conversion.
    """

    logger.info(f"Applying transformations for task: {task.id}.")

    if not task.transformations:
        logger.error(f"No transformations were applied for task: {task.id}.")
        raise NoTransformationsDefined(
            detail=f"No transformations were applied for task: {task.id}."
        )

    for transformation in task.transformations:
        operation = transformation.get("operation")
        params = transformation.get("params", {})

        if operation not in TRANSFORMATION_MAP:
            logger.error(f"Invalid operation: {operation} for task: {task.id}.")
            raise InvalidTransformation(
                f"Invalid operation: {operation} for task: {task.id}."
            )

        transform_func: TransformFunc = TRANSFORMATION_MAP[operation]

        logger.info(f"Applying transformation {operation} with params {params}")

        try:
            processed_image = transform_func(processed_image, **params)
            if not processed_image:
                logger.error(f"Transformation failed for task: {task.id}.")
                raise TransformationFailed(
                    detail=f"Transformation failed for task: {task.id}."
                )
        except Exception as e:
            logger.error(
                f"Error applying transformation {operation} for task: {task.id}: {e}",
                exc_info=True,
            )
            raise TransformationFailed(
                detail=f"Error applying transformation {operation} "
                f"for task: {task.id}: {e}"
            )

    # Ensure RGB mode if image is RGBA
    if processed_image and processed_image.mode == "RGBA":
        # This conversion can fail, handled this in the main except block.
        processed_image = processed_image.convert("RGB")
        if not processed_image:
            logger.error(f"Failed to convert image to RGB mode for task: {task.id}.")
            raise TransformationFailed(detail="Failed to convert image to RGB mode.")

    return processed_image


def _save_result_image(
    processed_image: Image.Image,
    task: TransformationTask,
    original_image_instance: SourceImage,
    image_format: str,
):
    """
    Saves image to buffer, creates Django File and TransformedImage record.
    """

    image_buffer = io.BytesIO()
    try:
        # Save to buffer
        processed_image.save(image_buffer, format=image_format)

        # Set format attribute
        processed_image.format = image_format

        # Reset buffer position
        image_buffer.seek(0)

        # Create filename
        file_name = (
            f"{original_image_instance.file_name}_{task.id}.{str(image_format).lower()}"
        )

        # Create Django File
        transformed_image_file = File(image_buffer, name=file_name)

        # Create TransformedImage record
        result_image = TransformedImage.objects.create(
            owner=task.owner,
            file=transformed_image_file,
            file_name=file_name,
            description=original_image_instance.description,
            source_image=original_image_instance,
            transformation_task=task,
            metadata=extract_metadata(image=processed_image),
        )
        result_image.save()

        return result_image

    finally:
        # Close the buffer to free up resources
        image_buffer.close()


@shared_task
def apply_transformations(task_id):
    """
    Receives the task id and applies the transformations
    according to the tranformations list by list order.

    Multiple transformations will be applied in serial fashion.
    Because seperating the transformations into different
    tasks will increase the image read/write and
    communication costs.

    Checks cache first to avoid re-computation
    and caching the result ID upon success.
    """
    task = None  # Define task in outer scope for exception handling
    try:
        # Step 1: Get task and set IN_PROGRESS
        task = _get_task_and_set_in_progress(task_id)

        # Check if transformation is already cached
        cached_image_id = get_transformed_image_id_from_cache(
            task.original_image.id, task.transformations, task.format
        )

        # If cached image ID is found, set it to task and don't apply transformations
        if cached_image_id:
            logger.info(
                f"Transformed image found in cache for task: {task.id}. "
                "Won't apply transformations."
            )
            task.result_image_id = cached_image_id
            task.status = TaskStatus.SUCCESS
            task.save()
            return

        # Step 2: Load image and determine format
        image, image_format, original_image_instance = _load_image_and_determine_format(
            task
        )

        # Step 3: Apply processing steps
        processed_image = _apply_processing_steps(image, task, image_format)

        # Step 4: Save result image
        transformed_image_instance = _save_result_image(
            processed_image, task, original_image_instance, image_format
        )

        # Step 5: Link result
        task.result_image = transformed_image_instance

        # Step 6: Save to cache
        set_transformed_image_id_to_cache(
            original_image_instance.id,
            task.transformations,
            task.format,
            transformed_image_instance.id,
        )

        task.status = TaskStatus.SUCCESS
        task.save()

    except Exception as e:
        logger.error(f"Error while applying transformations: {e}", exc_info=True)
        if task:
            task.status = TaskStatus.FAILED
            task.error_message = str(e)
            task.save()
        raise e


def crop(image: Image.Image, x, y, width, height) -> Image.Image | None:
    """
    Crop an image.
    """
    if x + width > image.width or y + height > image.height:
        raise ValueError("Invalid dimensions for cropping.")

    box = (x, y, x + width, y + height)
    return image.crop(box)


def resize(image: Image.Image, width, height) -> Image.Image | None:
    """
    Resize an image.
    """
    return image.resize((width, height))


def rotate(image: Image.Image, degrees) -> Image.Image | None:
    """
    Rotate an image.
    """
    return image.rotate(angle=degrees)


def watermark(image: Image.Image, watermark_text: str) -> Image.Image | None:
    """
    Applies a standard, semi-transparent, diagonal watermark text
    across the image center.

    Args:
        image: The base image to watermark.
        watermark_text: The text to use as a watermark.

    Returns:
        The watermarked image.
    """

    if not watermark_text:
        raise ValueError("Watermark text cannot be empty.")

    # make a blank image for the text, initialized to transparent text color
    watermark_image: Image.Image = Image.new("RGBA", image.size, (255, 255, 255, 0))

    # get a drawing context
    draw = ImageDraw.Draw(watermark_image)

    # get image size
    width, height = image.size

    # draw text in the center of the image
    draw.text((width / 2, height / 2), watermark_text, fill=(255, 255, 255, 128))

    # rotate text 45 degrees
    watermark_image = watermark_image.rotate(45)

    return Image.alpha_composite(image, watermark_image)


def flip(image: Image.Image) -> Image.Image | None:
    """
    Flip an image vertically (top to bottom).
    """
    return ImageOps.flip(image)


def mirror(image: Image.Image) -> Image.Image | None:
    """
    Mirror an image horizontally (left to right).
    """
    return ImageOps.mirror(image)


def grayscale(image: Image.Image) -> Image.Image | None:
    """
    Convert an image to grayscale.
    """
    return image.convert("L")


def sepia(image: Image.Image) -> Image.Image | None:
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


def blur(image: Image.Image) -> Image.Image | None:
    """
    Apply a blur filter to an image.
    """
    return image.filter(ImageFilter.GaussianBlur)


# Define available filters from ImageFilter
AVAILABLE_FILTERS: dict[str, TransformFunc] = {
    "BLUR": blur,
    "GRAYSCALE": grayscale,
    "SEPIA": sepia,
    # Add other filters as needed, e.g., GaussianBlur, UnsharpMask might need parameters
    # "GaussianBlur": ImageFilter.GaussianBlur, # Example: Needs radius parameter
}


def apply_filter(image: Image.Image, *args, **kwargs) -> Image.Image | None:
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
        filter_to_apply: TransformFunc | None = AVAILABLE_FILTERS.get(
            filter_name.upper()
        )
        if filter_to_apply:
            logger.info(f"Applying filter: {filter_name}")
            filtered_image = filter_to_apply(image)
            if not filtered_image:
                logger.error(f"Failed to apply filter: {filter_name}.")
                raise TransformationFailed(
                    detail=f"Failed to apply filter: {filter_name}."
                )
            image = filtered_image
        else:
            logger.error(f"Invalid filter name: {filter_name}. No filter applied.")
            raise InvalidTransformation(f"Invalid filter name: {filter_name}")

    return image


"""
The key is the name of the transformation function.
The value is the function itself.

This dictionary won't include the "change_format" transformation
because it's not a transformation function. And format change
is done in the apply_transformations function.
"""
TRANSFORMATION_MAP: dict[str, TransformFunc] = {
    "crop": crop,
    "resize": resize,
    "rotate": rotate,
    "watermark": watermark,
    "flip": flip,
    "mirror": mirror,
    "apply_filter": apply_filter,
}
