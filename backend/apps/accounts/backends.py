from django.contrib.auth.backends import ModelBackend

from .models import User


class EmailOrPhoneBackend(ModelBackend):
    """Authenticate with either an email address or a phone number."""

    def authenticate(self, request, username=None, password=None, **kwargs):
        identifier = username or kwargs.get(User.USERNAME_FIELD)
        if not identifier or password is None:
            return None
        user = User.objects.get_by_identifier(identifier)
        if user is None:
            # Hash anyway so response time does not reveal whether the account exists.
            User().set_password(password)
            return None
        if user.check_password(password) and self.user_can_authenticate(user):
            return user
        return None
