from django.contrib.auth import get_user_model
from django.core.exceptions import ImproperlyConfigured
from google.auth.transport import requests as google_requests
from google.oauth2 import id_token as google_id_token
from rest_framework import serializers
from rest_framework.exceptions import AuthenticationFailed
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.tokens import RefreshToken

from .conf import bodepontoio_settings
from .services.tokens import generate_tokens
from .tokens import check_confirmation_token, check_reset_token, decode_uid

User = get_user_model()


class LoginSerializer(serializers.Serializer):
    login = serializers.CharField()
    password = serializers.CharField(write_only=True)


class TokenRefreshSerializer(serializers.Serializer):
    refresh = serializers.CharField(write_only=True)

    def validate(self, attrs):
        try:
            token = RefreshToken(attrs["refresh"])
        except TokenError:
            raise AuthenticationFailed("Token inválido ou expirado.") from None
        attrs["token"] = token
        return attrs

    def to_representation(self, instance):
        token = instance["token"]
        return {
            "refresh": str(token),
            "access": str(token.access_token),
        }


class LogoutSerializer(serializers.Serializer):
    refresh = serializers.CharField()


class RegisterSerializer(serializers.ModelSerializer):
    username = serializers.CharField(required=False)
    email = serializers.EmailField(required=True)
    password = serializers.CharField(write_only=True, min_length=8)

    class Meta:
        model = User
        fields = ("username", "email", "password", "first_name", "last_name")

    def validate_username(self, value):
        if User.objects.filter(username=value).exists():
            raise serializers.ValidationError("Já existe um usuário com este nome de usuário.")
        return value

    def validate_email(self, value):
        if User.objects.filter(email=value).exists():
            raise serializers.ValidationError("Já existe um usuário com este e-mail.")
        return value

    def _unique_username(self, base: str) -> str:
        username = base
        suffix = 1
        while User.objects.filter(username=username).exists():
            username = f"{base}{suffix}"
            suffix += 1
        return username

    def create(self, validated_data):
        if not validated_data.get("username"):
            base = validated_data["email"].split("@")[0]
            validated_data["username"] = self._unique_username(base)

        return User.objects.create_user(**validated_data)


class PasswordChangeSerializer(serializers.Serializer):
    old_password = serializers.CharField(write_only=True)
    new_password = serializers.CharField(write_only=True, min_length=8)

    def validate_old_password(self, value):
        user = self.context["request"].user
        if not user.check_password(value):
            raise AuthenticationFailed("Senha antiga incorreta.")
        return value


class EmailConfirmSerializer(serializers.Serializer):
    uid = serializers.CharField()
    token = serializers.CharField()

    def validate(self, attrs):
        try:
            pk = decode_uid(attrs["uid"])
            user = User.objects.get(pk=pk)
        except (User.DoesNotExist, ValueError, TypeError, OverflowError, Exception):
            raise AuthenticationFailed("Link de confirmação inválido ou expirado.") from None
        if not check_confirmation_token(user, attrs["token"]):
            raise AuthenticationFailed("Link de confirmação inválido ou expirado.")
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
            raise AuthenticationFailed("Token de ID do Google inválido.") from None

        email = id_info["email"]
        first_name = id_info.get("given_name", "")
        last_name = id_info.get("family_name", "")
        user, created = User.objects.get_or_create(
            username=email,
            defaults={
                "email": email,
                "first_name": first_name,
                "last_name": last_name,
            },
        )

        if created:
            user.set_unusable_password()
            user.save(update_fields=["password"])

        profile, _ = user.auth.__class__.objects.get_or_create(user=user)
        profile.is_email_verified = True
        profile.save(update_fields=["is_email_verified"])

        if not user.is_active:
            raise AuthenticationFailed("Conta de usuário desativada.")

        attrs["user"] = user
        return attrs

    def to_representation(self, instance):
        return generate_tokens(instance["user"])


class PasswordlessLoginRequestSerializer(serializers.Serializer):
    email = serializers.EmailField()


class PasswordlessLoginConfirmSerializer(serializers.Serializer):
    email = serializers.EmailField()
    code = serializers.CharField(max_length=8)


class OTPEmailConfirmSerializer(serializers.Serializer):
    email = serializers.EmailField()
    code = serializers.CharField(max_length=8)


class OTPPasswordResetConfirmSerializer(serializers.Serializer):
    email = serializers.EmailField()
    code = serializers.CharField(max_length=8)
    new_password = serializers.CharField(write_only=True, min_length=8)


class PasswordResetConfirmSerializer(serializers.Serializer):
    uid = serializers.CharField()
    token = serializers.CharField()
    new_password = serializers.CharField(write_only=True, min_length=8)

    def validate(self, attrs):
        try:
            pk = decode_uid(attrs["uid"])
            user = User.objects.get(pk=pk)
        except (User.DoesNotExist, ValueError, TypeError, OverflowError, Exception):
            raise AuthenticationFailed("UID inválido.") from None
        if not check_reset_token(user, attrs["token"]):
            raise AuthenticationFailed("Token inválido ou expirado.")
        attrs["user"] = user
        return attrs
