from django.contrib.auth import get_user_model
from rest_framework import permissions, serializers, status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.tokens import RefreshToken

from .conf import bodepontoio_settings
from .emails import send_email_confirmation_email, send_password_reset_email
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
    PasswordResetConfirmSerializer,
    PasswordResetRequestSerializer,
    RegisterSerializer,
    ResendEmailConfirmationSerializer,
    TokenRefreshSerializer,
)

User = get_user_model()


class LoginView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        serializer = LoginSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        return Response(serializer.data)


class GoogleLoginView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        serializer = GoogleLoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
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
            raise serializers.ValidationError("Código inválido ou expirado.")

        success, error = verify_otp(user, serializer.validated_data["code"], OTPCode.Purpose.EMAIL_CONFIRM)
        if not success:
            raise serializers.ValidationError(error)

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
            raise serializers.ValidationError("Código inválido ou expirado.")

        success, error = verify_otp(user, serializer.validated_data["code"], OTPCode.Purpose.PASSWORD_RESET)
        if not success:
            raise serializers.ValidationError(error)

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
