from rest_framework import generics, permissions, status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework_simplejwt.tokens import RefreshToken

from api.models import SourceImage, TransformedImage
from api.permissions import IsOwner
from api.serializers import (
    LoginSerializer,
    RegisterSerializer,
    SourceImageDetailSerializer,
    SourceImageListSerializer,
    TransformedImageDetailSerializer,
    TransformedImageListSerializer,
    UploadImageSerializer,
)


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
                    "id": serializer.validated_data["user"].id,
                    "username": serializer.validated_data["user"].username,
                },
                "token": token,
            },
            status=status.HTTP_200_OK,
        )
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class SourceImageListView(generics.ListAPIView):
    """
    API view for listing and source images.
    """

    queryset = SourceImage.objects.all()
    serializer_class = SourceImageListSerializer
    permission_classes = [permissions.IsAuthenticated, IsOwner]


class SourceImageDetailView(generics.RetrieveAPIView):
    """
    API view for retrieving a source image.
    """

    queryset = SourceImage.objects.all()
    serializer_class = SourceImageDetailSerializer
    permission_classes = [permissions.IsAuthenticated, IsOwner]


@api_view(["POST"])
@permission_classes([permissions.IsAuthenticated])
def upload_image(request) -> Response:
    """
    API view for uploading an image.
    """

    serializer = UploadImageSerializer(data=request.data)

    if serializer.is_valid():
        serializer.save(owner=request.user)
        return Response(serializer.data, status=status.HTTP_201_CREATED)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class TransformedImageListView(generics.ListAPIView):
    """
    API view for listing and transformed images.
    """

    queryset = TransformedImage.objects.all()
    serializer_class = TransformedImageListSerializer
    permission_classes = [permissions.IsAuthenticated, IsOwner]


class TransformedImageDetailView(generics.RetrieveAPIView):
    """
    API view for retrieving a transformed image.
    """

    queryset = TransformedImage.objects.all()
    serializer_class = TransformedImageDetailSerializer
    permission_classes = [permissions.IsAuthenticated, IsOwner]
