from django.contrib.auth import get_user_model
from django.contrib.auth.signals import user_logged_in
from django.utils import timezone
from rest_framework import permissions, status
from rest_framework.exceptions import AuthenticationFailed
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.tokens import RefreshToken

from .conf import bodepontoio_settings
from .emails import (
    send_email_confirmation_email,
    send_login_email,
    send_password_reset_email,
)
from .models import OTPCode
from .otp import verify_otp
from .serializers import (
    EmailConfirmSerializer,
    GoogleLoginSerializer,
    LoginSerializer,
    LogoutSerializer,
    MagicLinkLoginConfirmSerializer,
    OTPEmailConfirmSerializer,
    OTPPasswordResetConfirmSerializer,
    PasswordChangeSerializer,
    PasswordlessLoginConfirmSerializer,
    PasswordlessLoginRequestSerializer,
    PasswordResetConfirmSerializer,
    PasswordResetRequestSerializer,
    RegisterSerializer,
    ResendEmailConfirmationSerializer,
    TokenRefreshSerializer,
)
from .throttles import LoginEmailThrottle, LoginIPThrottle
from .tokens import login_token_reuse_window
from .users import get_or_create_user_by_email

User = get_user_model()


def _record_login(request, user):
    """Fire the ``user_logged_in`` signal so LoginRecord (and Django's
    update_last_login) run for token-based logins, which never call
    ``django.contrib.auth.login()``."""
    user_logged_in.send(sender=user.__class__, request=request, user=user)


class PasswordlessLoginConfirmView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        if bodepontoio_settings.LOGIN_STRATEGY != "otp":
            return Response(status=status.HTTP_404_NOT_FOUND)

        serializer = PasswordlessLoginConfirmSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            user = User.objects.get(email=serializer.validated_data["email"])
        except User.DoesNotExist:
            raise AuthenticationFailed("Código inválido ou expirado.") from None

        if not user.is_active:
            raise AuthenticationFailed("Conta de usuário desativada.")

        success, error = verify_otp(user, serializer.validated_data["code"], OTPCode.Purpose.LOGIN)
        if not success:
            raise AuthenticationFailed(error)

        if not user.auth.is_email_verified:
            user.auth.is_email_verified = True
            user.auth.save(update_fields=["is_email_verified"])

        _record_login(request, user)
        from .serializers import _get_tokens
        return Response(_get_tokens(user))


class MagicLinkLoginConfirmView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        if bodepontoio_settings.LOGIN_STRATEGY != "magic_link":
            return Response(status=status.HTTP_404_NOT_FOUND)

        serializer = MagicLinkLoginConfirmSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.validated_data["user"]

        if not user.is_active:
            raise AuthenticationFailed("Conta de usuário desativada.")

        if not user.auth.is_email_verified:
            user.auth.is_email_verified = True
            user.auth.save(update_fields=["is_email_verified"])

        # Single-use comes from moving last_login, which is part of the token
        # hash; Django's update_last_login receiver normally does it, fired by
        # _record_login. If a project disconnects that receiver the guarantee
        # would vanish with no window configured and no error, so write it here
        # instead of trusting the signal. The reuse window opts out of the whole
        # mechanism; see LoginTokenGenerator.
        last_login_before = user.last_login
        _record_login(request, user)
        if not login_token_reuse_window() and user.last_login == last_login_before:
            user.last_login = timezone.now()
            user.save(update_fields=["last_login"])

        from .serializers import _get_tokens
        return Response(_get_tokens(user))


class LoginView(APIView):
    permission_classes = [permissions.AllowAny]
    throttle_classes = [LoginIPThrottle, LoginEmailThrottle]

    def post(self, request):
        if bodepontoio_settings.LOGIN_STRATEGY in ("otp", "magic_link"):
            serializer = PasswordlessLoginRequestSerializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            email = serializer.validated_data["email"]
            next_path = serializer.validated_data.get("next", "")
            if bodepontoio_settings.LOGIN_AUTO_SIGNUP:
                user, _created = get_or_create_user_by_email(email)
            else:
                user = User.objects.filter(email=email).first()
            if user is not None and user.is_active:
                send_login_email(user, next_path=next_path)
            if bodepontoio_settings.LOGIN_STRATEGY == "magic_link":
                msg = "Um link de acesso foi enviado para o seu e-mail."
            else:
                msg = "Um código de acesso foi enviado para o seu e-mail."
            return Response(msg)

        serializer = LoginSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        _record_login(request, serializer.validated_data["user"])
        return Response(serializer.data)


class LoginResendView(APIView):
    permission_classes = [permissions.AllowAny]
    throttle_classes = [LoginIPThrottle, LoginEmailThrottle]

    def post(self, request):
        if bodepontoio_settings.LOGIN_STRATEGY not in ("otp", "magic_link"):
            return Response(status=status.HTTP_404_NOT_FOUND)

        serializer = PasswordlessLoginRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        email = serializer.validated_data["email"]
        next_path = serializer.validated_data.get("next", "")

        user = User.objects.filter(email=email).first()
        if user is not None and user.is_active:
            send_login_email(user, next_path=next_path)

        if bodepontoio_settings.LOGIN_STRATEGY == "magic_link":
            msg = "Se esse e-mail existir, reenviamos um link de acesso."
        else:
            msg = "Se esse e-mail existir, reenviamos um código de acesso."
        return Response(msg)


class GoogleLoginView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        serializer = GoogleLoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        _record_login(request, serializer.validated_data["user"])
        return Response(serializer.data)


class TokenRefreshView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        serializer = TokenRefreshSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        return Response(serializer.data)


class LogoutView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        serializer = LogoutSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            token = RefreshToken(serializer.validated_data["refresh"])
            token.blacklist()
        except TokenError:
            return Response(
                "Token inválido ou expirado.",
                status=status.HTTP_400_BAD_REQUEST,
            )

        return Response()


class RegisterView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        serializer = RegisterSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        send_email_confirmation_email(user, request)

        return Response(
            "Cadastro realizado com sucesso. Verifique seu e-mail para confirmar sua conta.",
            status=status.HTTP_201_CREATED,
        )


class PasswordChangeView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        serializer = PasswordChangeSerializer(
            data=request.data, context={"request": request}
        )
        serializer.is_valid(raise_exception=True)
        request.user.set_password(serializer.validated_data["new_password"])
        request.user.save()
        return Response("Senha alterada com sucesso.")


class PasswordResetRequestView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        serializer = PasswordResetRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            user = User.objects.get(email=serializer.validated_data["email"])
            send_password_reset_email(user)
        except User.DoesNotExist:
            pass  # Anti-enumeration: always return 200
        if bodepontoio_settings.PASSWORD_RESET_STRATEGY == "otp":
            msg = "Se esse e-mail existir, um código de redefinição foi enviado."
        else:
            msg = "Se esse e-mail existir, um link de redefinição foi enviado."
        return Response(msg)


class PasswordResetConfirmView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        serializer = PasswordResetConfirmSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.validated_data["user"]
        user.set_password(serializer.validated_data["new_password"])
        user.save()
        return Response("Senha redefinida com sucesso.")


class EmailConfirmView(APIView):
    permission_classes = [permissions.AllowAny]

    def get(self, request, uid, token):
        serializer = EmailConfirmSerializer(data={"uid": uid, "token": token})
        serializer.is_valid(raise_exception=True)
        user = serializer.validated_data["user"]
        user.auth.is_email_verified = True
        user.auth.save(update_fields=["is_email_verified"])
        return Response("Endereço de e-mail confirmado.")


class OTPEmailConfirmView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        if bodepontoio_settings.EMAIL_CONFIRM_STRATEGY != "otp":
            return Response(status=status.HTTP_404_NOT_FOUND)

        serializer = OTPEmailConfirmSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            user = User.objects.get(email=serializer.validated_data["email"])
        except User.DoesNotExist:
            raise AuthenticationFailed("Código inválido ou expirado.") from None

        success, error = verify_otp(user, serializer.validated_data["code"], OTPCode.Purpose.EMAIL_CONFIRM)
        if not success:
            raise AuthenticationFailed(error)

        user.auth.is_email_verified = True
        user.auth.save(update_fields=["is_email_verified"])
        return Response("Endereço de e-mail confirmado.")


class OTPPasswordResetConfirmView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        if bodepontoio_settings.PASSWORD_RESET_STRATEGY != "otp":
            return Response(status=status.HTTP_404_NOT_FOUND)

        serializer = OTPPasswordResetConfirmSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            user = User.objects.get(email=serializer.validated_data["email"])
        except User.DoesNotExist:
            raise AuthenticationFailed("Código inválido ou expirado.") from None

        success, error = verify_otp(user, serializer.validated_data["code"], OTPCode.Purpose.PASSWORD_RESET)
        if not success:
            raise AuthenticationFailed(error)

        user.set_password(serializer.validated_data["new_password"])
        user.save()
        return Response("Senha redefinida com sucesso.")


class ResendEmailConfirmationView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        serializer = ResendEmailConfirmationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            user = User.objects.get(email=serializer.validated_data["email"])
            if not user.auth.is_email_verified:
                send_email_confirmation_email(user, request)
        except User.DoesNotExist:
            pass  # Anti-enumeration: always return 200
        if bodepontoio_settings.EMAIL_CONFIRM_STRATEGY == "otp":
            msg = "Se esse e-mail existir e não estiver confirmado, um código de confirmação foi enviado."
        else:
            msg = "Se esse e-mail existir e não estiver confirmado, um link de confirmação foi enviado."
        return Response(msg)
