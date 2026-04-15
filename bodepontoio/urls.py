from django.urls import path

from .views import (
    EmailConfirmView,
    GoogleLoginView,
    LoginView,
    LogoutView,
    OTPEmailConfirmView,
    OTPPasswordResetConfirmView,
    PasswordChangeView,
    PasswordlessLoginConfirmView,
    PasswordResetConfirmView,
    PasswordResetRequestView,
    RegisterView,
    ResendEmailConfirmationView,
    TokenRefreshView,
)

app_name = "bodepontoio"

urlpatterns = [
    path("login/otp/confirm/", PasswordlessLoginConfirmView.as_view(), name="login-otp-confirm"),
    path("login/", LoginView.as_view(), name="login"),
    path("token/refresh/", TokenRefreshView.as_view(), name="token-refresh"),
    path("social/google/", GoogleLoginView.as_view(), name="social-google"),
    path("logout/", LogoutView.as_view(), name="logout"),
    path("register/", RegisterView.as_view(), name="register"),
    path("password/change/", PasswordChangeView.as_view(), name="password-change"),
    path("password/reset/", PasswordResetRequestView.as_view(), name="password-reset"),
    path(
        "password/reset/confirm/",
        PasswordResetConfirmView.as_view(),
        name="password-reset-confirm",
    ),
    path(
        "email/confirm/resend/",
        ResendEmailConfirmationView.as_view(),
        name="email-confirm-resend",
    ),
    path(
        "email/confirm/otp/",
        OTPEmailConfirmView.as_view(),
        name="email-confirm-otp",
    ),
    path(
        "email/confirm/<str:uid>/<str:token>/",
        EmailConfirmView.as_view(),
        name="email-confirm",
    ),
    path(
        "password/reset/confirm/otp/",
        OTPPasswordResetConfirmView.as_view(),
        name="password-reset-confirm-otp",
    ),
]
