from django.contrib.auth import password_validation
from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import transaction
from rest_framework import serializers

from . import services
from .models import User, UserProfile
from .validators import normalize_phone

CONTACT_REQUIRED = "Provide an email or phone number (at least one)."


def _validate_password(password, user=None):
    try:
        password_validation.validate_password(password, user)
    except DjangoValidationError as exc:
        raise serializers.ValidationError({"password": list(exc.messages)}) from exc


class ContactFieldsMixin(serializers.Serializer):
    """Shared email/phone handling: normalize, check uniqueness, require at least one."""

    email = serializers.EmailField(required=False, allow_null=True, allow_blank=True)
    phone = serializers.CharField(required=False, allow_null=True, allow_blank=True, max_length=32)

    def _others(self):
        queryset = User.objects.all()
        instance = getattr(self, "instance", None)
        return queryset.exclude(pk=instance.pk) if instance else queryset

    def validate_email(self, value):
        value = (value or "").strip().lower() or None
        if value and self._others().filter(email=value).exists():
            raise serializers.ValidationError("An account with this email already exists.")
        return value

    def validate_phone(self, value):
        if not value or not value.strip():
            return None
        try:
            value = normalize_phone(value)
        except DjangoValidationError as exc:
            raise serializers.ValidationError(exc.messages) from exc
        if self._others().filter(phone=value).exists():
            raise serializers.ValidationError("An account with this phone number already exists.")
        return value

    def validate_contact(self, attrs):
        instance = getattr(self, "instance", None)
        email = attrs.get("email", instance.email if instance else None)
        phone = attrs.get("phone", instance.phone if instance else None)
        if not email and not phone:
            raise serializers.ValidationError({"non_field_errors": [CONTACT_REQUIRED]})


class UserProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserProfile
        fields = [
            "date_of_birth",
            "nationality",
            "address",
            "emergency_contact_name",
            "emergency_contact_phone",
        ]


class UserSerializer(serializers.ModelSerializer):
    """The authenticated user's own account. Only name and profile are editable here;
    role, status and contact channels are read-only (contact changes need verification)."""

    profile = UserProfileSerializer(required=False)
    email_verified = serializers.BooleanField(read_only=True)
    phone_verified = serializers.BooleanField(read_only=True)

    class Meta:
        model = User
        fields = [
            "id",
            "full_name",
            "email",
            "phone",
            "role",
            "email_verified",
            "phone_verified",
            "date_joined",
            "profile",
        ]
        read_only_fields = ["id", "email", "phone", "role", "date_joined"]

    @transaction.atomic
    def update(self, instance, validated_data):
        profile_data = validated_data.pop("profile", None)
        instance = super().update(instance, validated_data)
        if profile_data:
            for field, value in profile_data.items():
                setattr(instance.profile, field, value)
            instance.profile.save()
        return instance


class RegisterSerializer(ContactFieldsMixin):
    full_name = serializers.CharField(max_length=150)
    password = serializers.CharField(write_only=True, trim_whitespace=False)
    password_confirm = serializers.CharField(write_only=True, trim_whitespace=False)

    def validate(self, attrs):
        self.validate_contact(attrs)
        if attrs["password"] != attrs.pop("password_confirm"):
            raise serializers.ValidationError({"password_confirm": ["Passwords do not match."]})
        candidate = User(
            full_name=attrs["full_name"], email=attrs.get("email"), phone=attrs.get("phone")
        )
        _validate_password(attrs["password"], candidate)
        return attrs

    def create(self, validated_data):
        return services.register_user(**validated_data)


class LoginSerializer(serializers.Serializer):
    identifier = serializers.CharField(help_text="Email address or phone number.")
    password = serializers.CharField(write_only=True, trim_whitespace=False)


class LogoutSerializer(serializers.Serializer):
    refresh = serializers.CharField()


class TokenPairSerializer(serializers.Serializer):
    access = serializers.CharField()
    refresh = serializers.CharField()


class AuthResponseSerializer(serializers.Serializer):
    """Shape of register/login responses (documentation only)."""

    user = UserSerializer()
    tokens = TokenPairSerializer()


class NewPasswordMixin(serializers.Serializer):
    new_password = serializers.CharField(write_only=True, trim_whitespace=False)
    new_password_confirm = serializers.CharField(write_only=True, trim_whitespace=False)

    def validate_new_password_pair(self, attrs, user):
        if attrs["new_password"] != attrs["new_password_confirm"]:
            raise serializers.ValidationError({"new_password_confirm": ["Passwords do not match."]})
        try:
            password_validation.validate_password(attrs["new_password"], user)
        except DjangoValidationError as exc:
            raise serializers.ValidationError({"new_password": list(exc.messages)}) from exc


class PasswordChangeSerializer(NewPasswordMixin):
    current_password = serializers.CharField(write_only=True, trim_whitespace=False)

    def validate_current_password(self, value):
        if not self.context["request"].user.check_password(value):
            raise serializers.ValidationError("Current password is incorrect.")
        return value

    def validate(self, attrs):
        self.validate_new_password_pair(attrs, self.context["request"].user)
        return attrs


class PasswordResetRequestSerializer(serializers.Serializer):
    email = serializers.EmailField()


class PasswordResetConfirmSerializer(NewPasswordMixin):
    uid = serializers.CharField()
    token = serializers.CharField()

    def validate(self, attrs):
        user = services.get_user_for_reset(attrs["uid"], attrs["token"])
        if user is None:
            raise serializers.ValidationError(
                {"token": ["This reset link is invalid or has expired."]}
            )
        self.validate_new_password_pair(attrs, user)
        attrs["user"] = user
        return attrs


class AdminUserSerializer(ContactFieldsMixin, serializers.ModelSerializer):
    """User management for admins. Passwords are write-only and never returned."""

    password = serializers.CharField(write_only=True, required=False, trim_whitespace=False)
    email_verified = serializers.BooleanField(read_only=True)
    phone_verified = serializers.BooleanField(read_only=True)

    class Meta:
        model = User
        fields = [
            "id",
            "full_name",
            "email",
            "phone",
            "role",
            "is_active",
            "email_verified",
            "phone_verified",
            "date_joined",
            "last_login",
            "password",
        ]
        read_only_fields = ["id", "date_joined", "last_login"]

    def validate_role(self, value):
        actor = self.context["request"].user
        current = self.instance.role if self.instance else User.Role.USER
        if value != current and not actor.is_super_admin:
            raise serializers.ValidationError("Only a super admin can change roles.")
        return value

    def validate(self, attrs):
        self.validate_contact(attrs)
        password = attrs.get("password")
        if self.instance is None and not password:
            raise serializers.ValidationError({"password": ["This field is required."]})
        if password:
            _validate_password(password, self.instance)
        return attrs

    def create(self, validated_data):
        password = validated_data.pop("password")
        return User.objects.create_user(password=password, **validated_data)

    @transaction.atomic
    def update(self, instance, validated_data):
        password = validated_data.pop("password", None)
        was_active = instance.is_active
        instance = super().update(instance, validated_data)
        if password:
            services.set_password(instance, password)
        if was_active and not instance.is_active:
            services.revoke_refresh_tokens(instance)
        return instance
