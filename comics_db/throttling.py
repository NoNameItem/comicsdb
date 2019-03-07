from rest_framework import throttling


class AllowAdminThrottle(throttling.UserRateThrottle):
    def allow_request(self, request, view):
        if request.user.is_staff or request.user.profile.unlimited_api:
            return True
        return super().allow_request(request, view)
