from django.conf import settings
from django.contrib.auth import authenticate, get_user_model
from django.contrib.auth.models import AbstractUser
from django.contrib.auth.password_validation import validate_password
from rest_framework import serializers

from api.models import SourceImage, TransformedImage

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
        fields = ["file", "file_name", "description"]
        read_only_fields = ("owner",)
        extra_kwargs = {
            "file": {"required": True},
            "file_name": {"required": False},
            "description": {"required": True},
        }

    def create(self, validated_data):
        return super().create(validated_data)

    def validate_file(self, value):
        """
        Validate the file type and size.
        """

        # Validate the file type
        if value.content_type not in ["image/jpeg", "image/png"]:
            raise serializers.ValidationError(
                "Invalid file type. Expected a JPEG or PNG file.", code="invalid"
            )

        # Validate the file size
        if (
            value.image.width > settings.IMAGE_MAX_PIXEL_SIZE
            or value.image.height > settings.IMAGE_MAX_PIXEL_SIZE
        ):
            raise serializers.ValidationError(
                f"Invalid image pixel size. Expected a file with a maximum size of {settings.IMAGE_MAX_PIXEL_SIZE} pixels on each side.",
                code="invalid",
            )
        if (
            value.image.width < settings.IMAGE_MIN_PIXEL_SIZE
            or value.image.height < settings.IMAGE_MIN_PIXEL_SIZE
        ):
            raise serializers.ValidationError(
                f"Invalid image pixel size. Expected a file with a minimum size of {settings.IMAGE_MIN_PIXEL_SIZE} pixels on each side.",
                code="invalid",
            )

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
