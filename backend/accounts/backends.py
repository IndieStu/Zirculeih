from django.contrib.auth.backends import BaseBackend

from .models import User


class EmailBackend(BaseBackend):
    def authenticate(self, request, username=None, password=None, **kwargs):
        email = (username or kwargs.get("email") or "").strip().lower()
        user = User.objects.filter(email=email).first()
        if user is None:
            User().set_password(password)
            return None
        if user.check_password(password) and user.is_active:
            return user
        return None

    def get_user(self, user_id):
        return User.objects.filter(pk=user_id, is_active=True).first()
