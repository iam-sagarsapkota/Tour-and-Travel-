from django import forms
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as DjangoUserAdmin
from django.contrib.auth.forms import ReadOnlyPasswordHashField

from .models import User, UserProfile


class UserCreationForm(forms.ModelForm):
    password1 = forms.CharField(label="Password", widget=forms.PasswordInput)
    password2 = forms.CharField(label="Password confirmation", widget=forms.PasswordInput)

    class Meta:
        model = User
        fields = ("full_name", "email", "phone", "role")

    def clean(self):
        cleaned = super().clean()
        if not cleaned.get("email") and not cleaned.get("phone"):
            raise forms.ValidationError("Provide an email or phone number (at least one).")
        if cleaned.get("password1") != cleaned.get("password2"):
            self.add_error("password2", "Passwords do not match.")
        return cleaned

    def save(self, commit=True):
        user = super().save(commit=False)
        user.set_password(self.cleaned_data["password1"])
        if commit:
            user.save()
        return user


class UserChangeForm(forms.ModelForm):
    password = ReadOnlyPasswordHashField()

    class Meta:
        model = User
        fields = ("full_name", "email", "phone", "role", "is_active", "password")

    def clean(self):
        cleaned = super().clean()
        if not cleaned.get("email") and not cleaned.get("phone"):
            raise forms.ValidationError("Provide an email or phone number (at least one).")
        return cleaned


class UserProfileInline(admin.StackedInline):
    model = UserProfile
    can_delete = False


@admin.register(User)
class UserAdmin(DjangoUserAdmin):
    form = UserChangeForm
    add_form = UserCreationForm
    inlines = [UserProfileInline]

    list_display = ("full_name", "email", "phone", "role", "is_active", "date_joined")
    list_filter = ("role", "is_active")
    search_fields = ("full_name", "email", "phone")
    ordering = ("-date_joined",)
    readonly_fields = ("date_joined", "last_login", "email_verified_at", "phone_verified_at")
    filter_horizontal = ("groups", "user_permissions")

    fieldsets = (
        (None, {"fields": ("email", "phone", "password")}),
        ("Personal", {"fields": ("full_name",)}),
        ("Access", {"fields": ("role", "is_active", "groups", "user_permissions")}),
        (
            "Activity",
            {"fields": ("date_joined", "last_login", "email_verified_at", "phone_verified_at")},
        ),
    )
    add_fieldsets = (
        (
            None,
            {
                "classes": ("wide",),
                "fields": ("full_name", "email", "phone", "role", "password1", "password2"),
            },
        ),
    )

    def has_delete_permission(self, request, obj=None):
        return False  # deactivate accounts instead of deleting them
