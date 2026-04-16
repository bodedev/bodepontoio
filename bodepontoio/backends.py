from django.contrib.auth import get_user_model
from django.contrib.auth.backends import ModelBackend

User = get_user_model()


class EmailOrUsernameBackend(ModelBackend):
    def authenticate(self, request, username=None, password=None, **kwargs):
        if username and "@" in username:
            try:
                user = User.objects.get(email=username)
                username = user.username
            except User.DoesNotExist:
                return None
            
        return super().authenticate(request, username=username, password=password)
