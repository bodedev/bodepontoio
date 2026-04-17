from django.contrib.auth import get_user_model
from rest_framework import permissions, status
from rest_framework.exceptions import AuthenticationFailed
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.tokens import RefreshToken

from .conf import bodepontoio_settings
from .mixins import BodepontoioMixin
from .emails import send_email_confirmation_email, send_login_otp_email, send_password_reset_email
from .models import OTPCode
from .otp import verify_otp
from .serializers import (
    EmailConfirmSerializer,
    GoogleLoginSerializer,
    LoginSerializer,
    LogoutSerializer,
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

User = get_user_model()


class PasswordlessLoginConfirmView(BodepontoioMixin, APIView):
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

        from .serializers import _get_tokens
        return Response(_get_tokens(user))


class LoginView(BodepontoioMixin, APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        if bodepontoio_settings.LOGIN_STRATEGY == "otp":
            serializer = PasswordlessLoginRequestSerializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            try:
                user = User.objects.get(email=serializer.validated_data["email"])
                if user.is_active:
                    send_login_otp_email(user)
            except User.DoesNotExist:
                pass  # Anti-enumeration: always return 200
            return Response("Se esse e-mail existir, um código de acesso foi enviado.")

        serializer = LoginSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        return Response(serializer.data)


class GoogleLoginView(BodepontoioMixin, APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        serializer = GoogleLoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        return Response(serializer.data)


class TokenRefreshView(BodepontoioMixin, APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        serializer = TokenRefreshSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        return Response(serializer.data)


class LogoutView(BodepontoioMixin, APIView):
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


class RegisterView(BodepontoioMixin, APIView):
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


class PasswordChangeView(BodepontoioMixin, APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        serializer = PasswordChangeSerializer(
            data=request.data, context={"request": request}
        )
        serializer.is_valid(raise_exception=True)
        request.user.set_password(serializer.validated_data["new_password"])
        request.user.save()
        return Response("Senha alterada com sucesso.")


class PasswordResetRequestView(BodepontoioMixin, APIView):
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


class PasswordResetConfirmView(BodepontoioMixin, APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        serializer = PasswordResetConfirmSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.validated_data["user"]
        user.set_password(serializer.validated_data["new_password"])
        user.save()
        return Response("Senha redefinida com sucesso.")


class EmailConfirmView(BodepontoioMixin, APIView):
    permission_classes = [permissions.AllowAny]

    def get(self, request, uid, token):
        serializer = EmailConfirmSerializer(data={"uid": uid, "token": token})
        serializer.is_valid(raise_exception=True)
        user = serializer.validated_data["user"]
        user.auth.is_email_verified = True
        user.auth.save(update_fields=["is_email_verified"])
        return Response("Endereço de e-mail confirmado.")


class OTPEmailConfirmView(BodepontoioMixin, APIView):
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


class OTPPasswordResetConfirmView(BodepontoioMixin, APIView):
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


class ResendEmailConfirmationView(BodepontoioMixin, APIView):
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
