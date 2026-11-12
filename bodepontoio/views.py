from django.contrib.auth import get_user_model
from django.contrib.auth.signals import user_logged_in
from django.utils import timezone
from rest_framework import permissions, status
from rest_framework.exceptions import AuthenticationFailed, ValidationError
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.tokens import RefreshToken

from .conf import (
    PASSWORDLESS_STRATEGIES,
    bodepontoio_settings,
    is_hybrid_login,
    uses_magic_link,
)
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
    HybridLoginRequestSerializer,
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
    PasswordSetSerializer,
    RegisterSerializer,
    ResendEmailConfirmationSerializer,
    TokenRefreshSerializer,
)
from .throttles import LoginEmailThrottle, LoginIPThrottle
from .tokens import login_token_reuse_window
from .users import get_or_create_user_by_email, get_user_by_email

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

        user = get_user_by_email(serializer.validated_data["email"])
        if user is None:
            raise AuthenticationFailed("Código inválido ou expirado.")

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
        if not uses_magic_link():
            return Response(status=status.HTTP_404_NOT_FOUND)

        serializer = MagicLinkLoginConfirmSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.validated_data["user"]

        # In the hybrid strategy an account with a password logs in with it;
        # its magic links stop working. Setting the password already changes
        # the token hash, so this only guards links minted some other way.
        if is_hybrid_login() and user.has_usable_password():
            raise ValidationError("Link inválido ou expirado.")

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
        if is_hybrid_login():
            return self._hybrid(request)

        if bodepontoio_settings.LOGIN_STRATEGY in ("otp", "magic_link"):
            serializer = PasswordlessLoginRequestSerializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            email = serializer.validated_data["email"]
            next_path = serializer.validated_data.get("next", "")
            if bodepontoio_settings.LOGIN_AUTO_SIGNUP:
                user, _created = get_or_create_user_by_email(email)
            else:
                user = get_user_by_email(email)
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

    def _hybrid(self, request):
        """``LOGIN_STRATEGY = "password_or_magic_link"``.

        ``{email}`` answers which method the account uses: ``"password"`` when
        it has one (nothing is sent), otherwise ``"magic_link"`` after sending
        the link (creating the account first with LOGIN_AUTO_SIGNUP). This
        tells callers whether an email has a password; the login throttles are
        what keep that from being cheap to harvest.

        ``{email, password}`` logs in and returns the tokens, like the
        ``"password"`` strategy.
        """
        serializer = HybridLoginRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        email = serializer.validated_data["email"]

        if "password" in serializer.validated_data:
            login = LoginSerializer(
                data={"login": email, "password": serializer.validated_data["password"]},
                context={"request": request},
            )
            login.is_valid(raise_exception=True)
            _record_login(request, login.validated_data["user"])
            return Response(login.data)

        user = get_user_by_email(email)
        if user is not None and user.has_usable_password():
            return Response({"method": "password"})

        if user is None and bodepontoio_settings.LOGIN_AUTO_SIGNUP:
            user, _created = get_or_create_user_by_email(email)
        if user is not None and user.is_active:
            send_login_email(user, next_path=serializer.validated_data.get("next", ""))
        return Response(
            {
                "method": "magic_link",
                "message": "Um link de acesso foi enviado para o seu e-mail.",
            }
        )


class LoginResendView(APIView):
    permission_classes = [permissions.AllowAny]
    throttle_classes = [LoginIPThrottle, LoginEmailThrottle]

    def post(self, request):
        if bodepontoio_settings.LOGIN_STRATEGY not in PASSWORDLESS_STRATEGIES:
            return Response(status=status.HTTP_404_NOT_FOUND)

        serializer = PasswordlessLoginRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        email = serializer.validated_data["email"]
        next_path = serializer.validated_data.get("next", "")

        user = get_user_by_email(email)
        if is_hybrid_login():
            if user is not None and user.has_usable_password():
                return Response({"method": "password"})
            if user is not None and user.is_active:
                send_login_email(user, next_path=next_path)
            return Response(
                {
                    "method": "magic_link",
                    "message": "Se esse e-mail existir, reenviamos um link de acesso.",
                }
            )

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


class PasswordSetView(APIView):
    """First password for a passwordless account. Answers 400 once the account
    has one; from then on it is password/change/ or the reset flow.

    The current JWTs stay valid (SimpleJWT does not tie them to the password),
    so the caller stays logged in.
    """

    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        serializer = PasswordSetSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        request.user.set_password(serializer.validated_data["new_password"])
        request.user.save()
        return Response("Senha criada com sucesso.")


class PasswordResetRequestView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        serializer = PasswordResetRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = get_user_by_email(serializer.validated_data["email"])
        if user is not None:
            send_password_reset_email(user)
        # Anti-enumeration: always return 200
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
        # The reset link proves the inbox. In the hybrid strategy an account
        # created by auto-signup may never have opened a magic link, and
        # without this its new password would hit "e-mail não confirmado".
        if is_hybrid_login() and not user.auth.is_email_verified:
            user.auth.is_email_verified = True
            user.auth.save(update_fields=["is_email_verified"])
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

        user = get_user_by_email(serializer.validated_data["email"])
        if user is None:
            raise AuthenticationFailed("Código inválido ou expirado.")

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

        user = get_user_by_email(serializer.validated_data["email"])
        if user is None:
            raise AuthenticationFailed("Código inválido ou expirado.")

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
        user = get_user_by_email(serializer.validated_data["email"])
        if user is not None and not user.auth.is_email_verified:
            send_email_confirmation_email(user, request)
        # Anti-enumeration: always return 200
        if bodepontoio_settings.EMAIL_CONFIRM_STRATEGY == "otp":
            msg = "Se esse e-mail existir e não estiver confirmado, um código de confirmação foi enviado."
        else:
            msg = "Se esse e-mail existir e não estiver confirmado, um link de confirmação foi enviado."
        return Response(msg)
