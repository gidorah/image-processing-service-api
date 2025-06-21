"""
URL configuration for image_processing_service project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.1/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""

from django.contrib import admin
from django.urls import include, path
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
)

from api import views

router = DefaultRouter()
router.register(r"tasks", views.TransformationTaskViewSet, basename="task")


urlpatterns = [
    path("api/", include(router.urls)),
    path("admin/", admin.site.urls),
    path("api/token/", TokenObtainPairView.as_view(), name="token_obtain_pair"),
    path("api/token/refresh/", TokenRefreshView.as_view(), name="token_refresh"),
    path("api/auth/", include("dj_rest_auth.urls")),
    path("api/auth/registration/", include("dj_rest_auth.registration.urls")),
    # dj-rest-auth endpoints for cookie-based authentication
    path("api/images/", views.SourceImageListView.as_view(), name="source_image_list"),
    path(
        route="api/images/<int:pk>/",
        view=views.SourceImageDetailView.as_view(),
        name="source_image_detail",
    ),
    path(
        route="api/images/upload/",
        view=views.upload_image,
        name="source_image_upload",
    ),
    path(
        route="api/images/transformed/",
        view=views.TransformedImageListView.as_view(),
        name="transformed_image_list",
    ),
    path(
        route="api/images/transformed/<int:pk>/",
        view=views.TransformedImageDetailView.as_view(),
        name="transformed_image_detail",
    ),
    path(
        route="api/images/<int:pk>/transform/",
        view=views.create_transformed_image,
        name="create_transformed_image",
    ),
]
