import enum

from django.conf import settings
from django.contrib.auth import authenticate, get_user_model
from django.contrib.auth.models import AbstractUser
from django.contrib.auth.password_validation import validate_password
from PIL import Image
from rest_framework import serializers
from rest_framework.exceptions import NotFound

from api.exceptions import FileSizeExceededError
from api.models import SourceImage, TransformationTask, TransformedImage
from utils.security import (
    escape_html_content,
    sanitize_filename,
    sanitize_metadata,
    sanitize_transformations,
)
from utils.utils import extract_metadata

User = get_user_model()


class RegisterSerializer(serializers.ModelSerializer):
    """
    Serializer for user registration.
    """

    password = serializers.CharField(write_only=True)

    class Meta:
        model = User
        fields = ("username", "password")

    def validate(self, attrs):
        """
        Validate the password strength.
        """
        user = User(username=attrs.get("username"))
        validate_password(attrs["password"], user)
        return attrs

    def create(self, validated_data) -> AbstractUser:
        user = User.objects.create_user(
            username=validated_data["username"],
            password=validated_data["password"],
        )

        return user


class LoginSerializer(serializers.Serializer):
    """
    Serializer for user login.
    """

    username = serializers.CharField(max_length=255)
    password = serializers.CharField(write_only=True)

    def validate(self, attrs):
        """
        Validate the username and password and authenticate the user.
        """
        username = attrs.get("username")
        password = attrs.get("password")

        if username and password:
            user = authenticate(
                request=self.context.get("request"),
                username=username,
                password=password,
            )

            if not user:
                raise serializers.ValidationError(
                    detail="Given username or password is wrong.",
                    code="INVALID_CREDENTIALS",
                )
        else:
            raise serializers.ValidationError(
                "Must include username and password.", code="MISSING_CREDENTIALS"
            )

        attrs["user"] = user
        return attrs


class SourceImageListSerializer(serializers.ModelSerializer):
    """
    Serializer for SourceImage model for listing.
    """

    class Meta:
        model = SourceImage
        fields = ["id", "file_name", "description", "file", "owner"]
        read_only_fields = ("owner", "id")


class SourceImageDetailSerializer(serializers.ModelSerializer):
    """
    Serializer for SourceImage model for detail.
    """

    class Meta:
        model = SourceImage
        fields = [
            "id",
            "file_name",
            "description",
            "file",
            "owner",
            "metadata",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ("owner", "id")
        extra_kwargs = {
            "url": {"required": False},
            "metadata": {"required": False},
        }


class UploadImageSerializer(serializers.ModelSerializer):
    """
    Serializer for uploading an image.
    """

    class Meta:
        model = SourceImage
        fields = ["id", "file", "file_name", "description"]
        read_only_fields = ("owner",)
        extra_kwargs = {
            "file": {"required": True},
            "file_name": {"required": False},
            "description": {"required": True},
        }

    def validate_file_name(self, value):
        """
        Sanitize the filename to prevent security issues.
        """
        if value:
            # Check for double extensions
            if value.count(".") > 1:
                raise serializers.ValidationError(
                    "Double extensions are not allowed in filenames", code="invalid"
                )

            return sanitize_filename(value)
        return value

    def validate_description(self, value):
        """
        Escape HTML content in description to prevent XSS.
        """
        return escape_html_content(value)

    def create(self, validated_data):
        # Extract and set metadata
        metadata = extract_metadata(image=validated_data["file"].image)
        # Sanitize metadata to prevent XSS
        validated_data["metadata"] = sanitize_metadata(metadata)
        return super().create(validated_data)

    def _check_executable_signatures(self, value):
        """Check for executable signatures in the file."""

        # Check for executable signatures in the first few bytes
        value.seek(0)
        header = value.read(512)  # Read first 512 bytes
        value.seek(0)

        # Check for common executable signatures
        executable_signatures = [
            b"MZ",  # PE (Windows)
            b"\x7fELF",  # ELF (Linux)
            b"\xfe\xed\xfa\xce",  # Mach-O (macOS)
            b"\xca\xfe\xba\xbe",  # Java class
            b"#!/",  # Shebang scripts
        ]

        for sig in executable_signatures:
            if header.startswith(sig):
                raise serializers.ValidationError(
                    "File contains executable signatures", code="invalid"
                )

        value.seek(0)

    def validate_file(self, value):
        """
        Validate the file type and size using PIL.
        """

        # First check for executable signatures for
        # polyglot files that could be interpreted as images
        # but are actually executable files
        self._check_executable_signatures(value)

        # Try opening with PIL to verify it's a valid image
        with Image.open(value) as img:
            if img.format and img.format.lower() not in ["jpeg", "png"]:
                raise serializers.ValidationError(
                    "Invalid file type. Expected a JPEG or PNG file.",
                    code="invalid",
                )

            # Validate the image size
            if value.size > settings.IMAGE_MAX_FILE_SIZE_IN_BYTES:
                raise FileSizeExceededError()

            # Validate the image dimensions
            if (
                img.width > settings.IMAGE_MAX_PIXEL_SIZE
                or img.height > settings.IMAGE_MAX_PIXEL_SIZE
            ):
                raise serializers.ValidationError(
                    (
                        f"Invalid image pixel size. Maximum allowed is "
                        f"{settings.IMAGE_MAX_PIXEL_SIZE} pixels per side."
                    ),
                    code="invalid",
                )
            if (
                img.width < settings.IMAGE_MIN_PIXEL_SIZE
                or img.height < settings.IMAGE_MIN_PIXEL_SIZE
            ):
                raise serializers.ValidationError(
                    (
                        f"Invalid image pixel size. Minimum required is "
                        f"{settings.IMAGE_MIN_PIXEL_SIZE} pixels per side."
                    ),
                    code="invalid",
                )

        # Reset file pointer for further processing
        value.seek(0)
        return value


class TransformedImageListSerializer(serializers.ModelSerializer):
    """
    Serializer for TranformedImage model for listing.
    """

    class Meta:
        model = TransformedImage
        fields = ["id", "file_name", "description", "file", "owner"]
        read_only_fields = ("owner", "id")


class TransformedImageDetailSerializer(serializers.ModelSerializer):
    """
    Serializer for TransformedImage model for detail.
    """

    class Meta:
        model = TransformedImage
        fields = [
            "id",
            "file_name",
            "description",
            "file",
            "owner",
            "metadata",
            "created_at",
            "updated_at",
            "source_image",
            "transformation_task",
        ]
        read_only_fields = ("owner", "id")


class ImageFormat(enum.Enum):
    """
    Image format choices to validate the format of the image
    """

    JPEG = "JPEG"
    PNG = "PNG"

    def __str__(self):
        return self.value


class TransformationTaskSerializer(serializers.ModelSerializer):
    """
    Serializer for TransformationTask model for detail.
    Handles associating the original_image based on the pk from the URL context.
    """

    class Meta:
        model = TransformationTask
        fields = [
            "id",
            "original_image",
            "result_image",
            "status",
            "transformations",
            "format",
            "created_at",
            "updated_at",
            "error_message",
        ]
        read_only_fields = (
            "id",
            "original_image",
            "result_image",
            "status",
            "created_at",
            "updated_at",
            "error_message",
        )

    def validate_transformations(self, value):
        """
        Sanitize transformations to prevent XSS and injection attacks.
        """
        return sanitize_transformations(value)

    def create(self, validated_data):
        """
        Create a TransformationTask, associating the SourceImage
        using the 'pk' from the context.
        """
        source_image_id = self.context.get("pk")
        if not source_image_id:
            raise serializers.ValidationError(
                "Could not determine the source image ID from the context."
            )

        try:
            source_image = SourceImage.objects.get(pk=source_image_id)
            # Check ownership if necessary (though view permission should handle this)
            request_user = self.context["request"].user
            if source_image.owner != request_user:
                raise serializers.ValidationError("You do not own this source image.")

        # if the source image does not exist, raise a not found error
        except SourceImage.DoesNotExist:
            raise NotFound(
                detail=f"Source image with ID {source_image_id} does not exist."
            )
        # Add owner and original_image to the validated_data before creating
        validated_data["owner"] = request_user
        validated_data["original_image"] = source_image
        return super().create(validated_data)

    def validate_format(self, value: str) -> str:
        """
        Validate the format of the image.
        """
        # Convert to uppercase for uniformity
        # and to avoid case-sensitive comparison

        if value.upper() not in [member.value for member in ImageFormat]:
            raise serializers.ValidationError(
                f"Invalid format. Expected one of {
                    [member.value for member in ImageFormat]
                }."
            )
        return value.upper()
