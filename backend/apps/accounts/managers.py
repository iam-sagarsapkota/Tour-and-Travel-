from django.contrib.auth.base_user import BaseUserManager
from django.core.exceptions import ValidationError

from .validators import normalize_phone


class UserManager(BaseUserManager):
    use_in_migrations = True

    def create_user(self, email=None, password=None, *, phone=None, **extra_fields):
        if not email and not phone:
            raise ValueError("Users must have an email or phone number.")
        user = self.model(email=email, phone=phone, **extra_fields)
        user.set_password(password)  # None -> unusable password
        user.save(using=self._db)
        return user

    def create_superuser(self, email=None, password=None, **extra_fields):
        extra_fields["role"] = self.model.Role.SUPER_ADMIN
        return self.create_user(email, password, **extra_fields)

    def get_by_identifier(self, identifier):
        """Look a user up by email or phone number; return None when there is no match."""
        identifier = (identifier or "").strip()
        if "@" in identifier:
            return self.filter(email=identifier.lower()).first()
        try:
            return self.filter(phone=normalize_phone(identifier)).first()
        except ValidationError:
            return None
