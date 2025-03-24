from rest_framework import generics, permissions, status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework_simplejwt.tokens import RefreshToken

from api.models import User
from api.serializers import LoginSerializer, RegisterSerializer


def get_tokens_for_user(user) -> dict[str, str]:
    """
    Get the access and refresh tokens for a user.
    """
    refresh = RefreshToken.for_user(user)

    return {
        "refresh": str(refresh),
        "access": str(refresh.access_token),
    }


@api_view(["POST"])
@permission_classes([permissions.AllowAny])
def register_user(request) -> Response:
    """
    API view for user registration.
    """

    serializer = RegisterSerializer(data=request.data)
    if serializer.is_valid():
        user = serializer.save()  # Returns the user instance
        token = get_tokens_for_user(user)
        return Response(
            {"user": serializer.data, "token": token}, status=status.HTTP_201_CREATED
        )
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(["POST"])
@permission_classes(permission_classes=[permissions.AllowAny])
def login_user(request) -> Response:
    """
    API view for user login.
    """

    serializer = LoginSerializer(data=request.data, context={"request": request})

    if serializer.is_valid():
        user = serializer.validated_data["user"]

        token = get_tokens_for_user(user)

        return Response(
            {
                "user": {
                    serializer.validated_data["username"],
                },
                "token": token,
            },
            status=status.HTTP_200_OK,
        )
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
