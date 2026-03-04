from django.urls import path

from .views import (
    EmailConfirmView,
    LoginView,
    LogoutView,
    PasswordChangeView,
    PasswordResetConfirmView,
    PasswordResetRequestView,
    RegisterView,
    ResendEmailConfirmationView,
)

app_name = "bodepontoio"

urlpatterns = [
    path("login/", LoginView.as_view(), name="login"),
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
        "email/confirm/<str:uid>/<str:token>/",
        EmailConfirmView.as_view(),
        name="email-confirm",
    ),
]
