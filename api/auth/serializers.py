import logging

from dj_rest_auth.registration.serializers import RegisterSerializer
from django.contrib.auth import get_user_model
from django.utils.translation import gettext_lazy as _
from rest_framework import serializers

logger = logging.getLogger(__name__)


class CustomRegisterSerializer(RegisterSerializer):
    """
    Extends dj_rest_auth's RegisterSerializer so that we also check
    the User table for duplicates (not only allauth's EmailAddress).
    """

    def validate_email(self, email):
        logger.debug("CustomRegisterSerializer.validate_email called")
        # Keep existing allauth checks
        email = super().validate_email(email)

        # Check against User table
        if get_user_model().objects.filter(email__iexact=email).exists():
            raise serializers.ValidationError(
                _("A user is already registered with this e-mail address.")
            )
        return email
