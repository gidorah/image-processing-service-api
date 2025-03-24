from django.contrib.auth import authenticate, get_user_model
from django.contrib.auth.models import AbstractUser
from django.contrib.auth.password_validation import validate_password
from rest_framework import serializers

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
