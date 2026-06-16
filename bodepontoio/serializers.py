from django.contrib.auth import authenticate, get_user_model
from django.core.exceptions import ImproperlyConfigured
from django.utils.module_loading import import_string
from google.auth.transport import requests as google_requests
from google.oauth2 import id_token as google_id_token
from rest_framework import serializers
from rest_framework.exceptions import AuthenticationFailed
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.tokens import RefreshToken

from .conf import bodepontoio_settings
from .tokens import check_confirmation_token, check_login_token, check_reset_token, decode_uid
from .users import get_or_create_user_by_email, has_username_field, unique_username_for_email

User = get_user_model()


class DefaultUserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ("id", "email", "first_name", "last_name")


def get_user_serializer_class():
    dotted_path = bodepontoio_settings.USER_SERIALIZER
    if dotted_path is None:
        return None
    try:
        return import_string(dotted_path)
    except ImportError as e:
        raise ImproperlyConfigured(
            f"Could not import USER_SERIALIZER '{dotted_path}': {e}"
        ) from e


def _get_tokens(user):
    refresh = RefreshToken.for_user(user)
    data = {
        "refresh": str(refresh),
        "access": str(refresh.access_token),
    }
    serializer_class = get_user_serializer_class()
    if serializer_class is not None:
        data["user"] = serializer_class(user).data
    return data


class LoginSerializer(serializers.Serializer):
    login = serializers.CharField()
    password = serializers.CharField(write_only=True)

    def validate(self, attrs):
        login = attrs["login"]
        try:
            user_obj = User.objects.get(email=login)
        except User.DoesNotExist:
            user_obj = None
            if has_username_field():
                try:
                    user_obj = User.objects.get(username=login)
                except User.DoesNotExist:
                    user_obj = None
            if user_obj is None:
                raise serializers.ValidationError("Credenciais inválidas.") from None

        user = authenticate(
            request=self.context.get("request"),
            username=getattr(user_obj, User.USERNAME_FIELD),
            password=attrs["password"],
        )

        if not user:
            raise serializers.ValidationError("Credenciais inválidas.")
        if not user.is_active:
            raise serializers.ValidationError("Conta de usuário desativada.")
        if not user.auth.is_email_verified:
            raise serializers.ValidationError("Endereço de e-mail não confirmado.")
        attrs["user"] = user
        return attrs

    def to_representation(self, instance):
        return _get_tokens(instance["user"])


class TokenRefreshSerializer(serializers.Serializer):
    refresh = serializers.CharField(write_only=True)

    def validate(self, attrs):
        try:
            token = RefreshToken(attrs["refresh"])
        except TokenError:
            raise serializers.ValidationError("Token inválido ou expirado.") from None
        attrs["token"] = token
        return attrs

    def to_representation(self, instance):
        token = instance["token"]
        data = {
            "refresh": str(token),
            "access": str(token.access_token),
        }
        serializer_class = get_user_serializer_class()
        if serializer_class is not None:
            try:
                user = User.objects.get(pk=token["user_id"])
            except User.DoesNotExist:
                pass
            else:
                data["user"] = serializer_class(user).data
        return data


class LogoutSerializer(serializers.Serializer):
    refresh = serializers.CharField()


class RegisterSerializer(serializers.ModelSerializer):
    email = serializers.EmailField(required=True)
    password = serializers.CharField(write_only=True, min_length=8)

    class Meta:
        model = User
        fields = ("email", "password", "first_name", "last_name")
        if has_username_field():
            fields = ("username",) + fields

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if has_username_field() and "username" in self.fields:
            self.fields["username"].required = False

    def validate_username(self, value):
        if User.objects.filter(username=value).exists():
            raise serializers.ValidationError("Já existe um usuário com este nome de usuário.")
        return value

    def validate_email(self, value):
        if User.objects.filter(email=value).exists():
            raise serializers.ValidationError("Já existe um usuário com este e-mail.")
        return value

    def create(self, validated_data):
        if has_username_field() and not validated_data.get("username"):
            validated_data["username"] = unique_username_for_email(validated_data["email"])

        return User.objects.create_user(**validated_data)


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
            ) from None
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
            raise AuthenticationFailed("Token de ID do Google inválido.") from None

        email = id_info["email"]
        first_name = id_info.get("given_name", "")
        last_name = id_info.get("family_name", "")
        user, _created = get_or_create_user_by_email(
            email,
            first_name=first_name,
            last_name=last_name,
        )

        profile, _ = user.auth.__class__.objects.get_or_create(user=user)
        profile.is_email_verified = True
        profile.save(update_fields=["is_email_verified"])

        if not user.is_active:
            raise AuthenticationFailed("Conta de usuário desativada.")

        attrs["user"] = user
        return attrs

    def to_representation(self, instance):
        return _get_tokens(instance["user"])


class PasswordlessLoginRequestSerializer(serializers.Serializer):
    email = serializers.EmailField()
    next = serializers.CharField(required=False, allow_blank=True, max_length=2000)

    def validate_next(self, value):
        if not value:
            return ""
        if not value.startswith("/") or value.startswith("//") or "://" in value or "\\" in value:
            raise serializers.ValidationError(
                "O destino deve ser um caminho relativo iniciado por '/'."
            )
        return value


class PasswordlessLoginConfirmSerializer(serializers.Serializer):
    email = serializers.EmailField()
    code = serializers.CharField(max_length=8)


class MagicLinkLoginConfirmSerializer(serializers.Serializer):
    uid = serializers.CharField()
    token = serializers.CharField()

    def validate(self, attrs):
        try:
            pk = decode_uid(attrs["uid"])
            user = User.objects.get(pk=pk)
        except (User.DoesNotExist, ValueError, TypeError, OverflowError, Exception):
            raise serializers.ValidationError("Link inválido ou expirado.") from None
        if not check_login_token(user, attrs["token"]):
            raise serializers.ValidationError("Link inválido ou expirado.")
        attrs["user"] = user
        return attrs


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
            raise serializers.ValidationError("UID inválido.") from None
        if not check_reset_token(user, attrs["token"]):
            raise serializers.ValidationError("Token inválido ou expirado.")
        attrs["user"] = user
        return attrs
