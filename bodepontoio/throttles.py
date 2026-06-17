from rest_framework.throttling import SimpleRateThrottle

from .conf import bodepontoio_settings


class _ConfiguredRateThrottle(SimpleRateThrottle):
    setting_name = ""
    cache_format = "throttle_%(scope)s_%(ident)s"

    def __init__(self):
        self.rate = getattr(bodepontoio_settings, self.setting_name) or None
        if self.rate:
            self.num_requests, self.duration = self.parse_rate(self.rate)
        else:
            self.num_requests, self.duration = None, None

    def allow_request(self, request, view):
        if not self.rate:
            return True
        return super().allow_request(request, view)


class LoginIPThrottle(_ConfiguredRateThrottle):
    scope = "bodepontoio_login_ip"
    setting_name = "LOGIN_THROTTLE_IP_RATE"

    def get_cache_key(self, request, view):
        ident = self.get_ident(request)
        return self.cache_format % {"scope": self.scope, "ident": ident}


class LoginEmailThrottle(_ConfiguredRateThrottle):
    scope = "bodepontoio_login_email"
    setting_name = "LOGIN_THROTTLE_EMAIL_RATE"

    def get_cache_key(self, request, view):
        email = (request.data.get("email") or "").strip().lower()
        if not email:
            return None
        return self.cache_format % {"scope": self.scope, "ident": email}
