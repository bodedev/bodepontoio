from django.contrib.auth import authenticate, get_user_model
from django.core.exceptions import ImproperlyConfigured
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
            raise serializers.ValidationError("Credenciais inválidas.")
        if not user.is_active:
            raise serializers.ValidationError("Conta de usuário desativada.")
        attrs["user"] = user
        return attrs

    def to_representation(self, instance):
        return _get_tokens(instance["user"])


class LogoutSerializer(serializers.Serializer):
    refresh = serializers.CharField()


class RegisterSerializer(serializers.ModelSerializer):
    email = serializers.EmailField(required=True)
    password = serializers.CharField(write_only=True, min_length=8)

    class Meta:
        model = User
        fields = ("email", "password", "first_name", "last_name")

    def validate_email(self, value):
        if User.objects.filter(username=value).exists():
            raise serializers.ValidationError("Já existe um usuário com este e-mail.")
        return value

    def create(self, validated_data):
        return User.objects.create_user(username=validated_data["email"], **validated_data)


class PasswordChangeSerializer(serializers.Serializer):
    old_password = serializers.CharField(write_only=True)
    new_password = serializers.CharField(write_only=True, min_length=8)

    def validate_old_password(self, value):
        user = self.context["request"].user
        if not user.check_password(value):
            raise serializers.ValidationError("Senha antiga incorreta.")
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
                "Link de confirmação inválido ou expirado."
            )
        if not check_confirmation_token(user, attrs["token"]):
            raise serializers.ValidationError(
                "Link de confirmação inválido ou expirado."
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
            raise AuthenticationFailed("Token de ID do Google inválido.")

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

        if not user.is_active:
            raise AuthenticationFailed("Conta de usuário desativada.")

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
            raise serializers.ValidationError("UID inválido.")
        if not check_reset_token(user, attrs["token"]):
            raise serializers.ValidationError("Token inválido ou expirado.")
        attrs["user"] = user
        return attrs
