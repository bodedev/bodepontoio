from rest_framework_simplejwt.tokens import RefreshToken


def generate_tokens(user) -> dict:
    refresh = RefreshToken.for_user(user)
    return {
        "refresh": str(refresh),
        "access": str(refresh.access_token),
    }
