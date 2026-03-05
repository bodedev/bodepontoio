from django.contrib.auth import authenticate, get_user_model
from django.core.exceptions import ImproperlyConfigured
from django.utils.translation import gettext_lazy as _
from google.auth.transport import requests as google_requests
from google.oauth2 import id_token as google_id_token
from rest_framework import serializers
from rest_framework.exceptions import AuthenticationFailed
from rest_framework_simplejwt.tokens import RefreshToken

from .conf import bodepontoio_settings
from .tokens import check_confirmation_token, check_reset_token, decode_uid

User = get_user_model()


def _get_tokens(user):
    refresh = RefreshToken.for_user(user)
    return {
        "refresh": str(refresh),
        "access": str(refresh.access_token),
    }


class LoginSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)

    def validate(self, attrs):
        user = authenticate(
            request=self.context.get("request"),
            username=attrs["email"],
            password=attrs["password"],
        )
        if not user:
            raise serializers.ValidationError(_("Invalid credentials."))
        if not user.is_active:
            raise serializers.ValidationError(_("User account is disabled."))
        if not user.is_email_verified:
            raise serializers.ValidationError(_("Email address is not confirmed."))
        attrs["user"] = user
        return attrs

    def to_representation(self, instance):
        return _get_tokens(instance["user"])


class LogoutSerializer(serializers.Serializer):
    refresh = serializers.CharField()


class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, min_length=8)

    class Meta:
        model = User
        fields = ("email", "password", "first_name", "last_name")

    def create(self, validated_data):
        return User.objects.create_user(**validated_data)


class PasswordChangeSerializer(serializers.Serializer):
    old_password = serializers.CharField(write_only=True)
    new_password = serializers.CharField(write_only=True, min_length=8)

    def validate_old_password(self, value):
        user = self.context["request"].user
        if not user.check_password(value):
            raise serializers.ValidationError(_("Old password is incorrect."))
        return value


class EmailConfirmSerializer(serializers.Serializer):
    uid = serializers.CharField()
    token = serializers.CharField()

    def validate(self, attrs):
        try:
            pk = decode_uid(attrs["uid"])
            user = User.objects.get(pk=pk)
        except (User.DoesNotExist, ValueError, TypeError, OverflowError, Exception):
            raise serializers.ValidationError(
                _("Invalid or expired confirmation link.")
            )
        if not check_confirmation_token(user, attrs["token"]):
            raise serializers.ValidationError(
                _("Invalid or expired confirmation link.")
            )
        attrs["user"] = user
        return attrs


class ResendEmailConfirmationSerializer(serializers.Serializer):
    email = serializers.EmailField()


class PasswordResetRequestSerializer(serializers.Serializer):
    email = serializers.EmailField()


class GoogleLoginSerializer(serializers.Serializer):
    id_token = serializers.CharField(write_only=True)

    def validate(self, attrs):
        client_id = bodepontoio_settings.GOOGLE_CLIENT_ID

        if not client_id:
            raise ImproperlyConfigured("BODEPONTOIO['GOOGLE_CLIENT_ID'] is not set.")

        try:
            id_info = google_id_token.verify_oauth2_token(
                attrs["id_token"], google_requests.Request(), client_id
            )

        except ValueError:
            raise AuthenticationFailed(_("Invalid Google ID token."))

        email = id_info["email"]
        first_name = id_info.get("given_name", "")
        last_name = id_info.get("family_name", "")
        user, created = User.objects.get_or_create(
            email=email,
            defaults={
                "first_name": first_name,
                "last_name": last_name,
                "is_email_verified": True,
            },
        )

        if created:
            user.set_unusable_password()
            user.save(update_fields=["password"])
        elif not user.is_email_verified:
            user.is_email_verified = True
            user.save(update_fields=["is_email_verified"])

        if not user.is_active:
            raise AuthenticationFailed(_("User account is disabled."))

        attrs["user"] = user
        return attrs

    def to_representation(self, instance):
        return _get_tokens(instance["user"])


class PasswordResetConfirmSerializer(serializers.Serializer):
    uid = serializers.CharField()
    token = serializers.CharField()
    new_password = serializers.CharField(write_only=True, min_length=8)

    def validate(self, attrs):
        try:
            pk = decode_uid(attrs["uid"])
            user = User.objects.get(pk=pk)
        except (User.DoesNotExist, ValueError, TypeError, OverflowError, Exception):
            raise serializers.ValidationError(_("Invalid uid."))
        if not check_reset_token(user, attrs["token"]):
            raise serializers.ValidationError(_("Invalid or expired token."))
        attrs["user"] = user
        return attrs
