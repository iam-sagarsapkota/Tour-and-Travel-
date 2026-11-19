from drf_spectacular.utils import extend_schema
from rest_framework import generics, status, viewsets
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenRefreshView as SimpleJWTRefreshView

from apps.operations.audit import AuditedViewSetMixin, record

from . import services
from .models import User
from .permissions import CanManageUser, IsAdmin
from .serializers import (
    AdminUserSerializer,
    AuthResponseSerializer,
    LoginSerializer,
    LogoutSerializer,
    PasswordChangeSerializer,
    PasswordResetConfirmSerializer,
    PasswordResetRequestSerializer,
    RegisterSerializer,
    SessionSerializer,
    TokenPairSerializer,
    UserSerializer,
    VerifyEmailSerializer,
)


def _auth_payload(user, request):
    return {
        "user": UserSerializer(user, context={"request": request}).data,
        "tokens": services.issue_tokens(user),
    }


class PublicAuthView(APIView):
    """Base for endpoints used before the client has a token."""

    authentication_classes = []
    permission_classes = [AllowAny]


class RegisterView(PublicAuthView):
    throttle_scope = "auth_register"

    @extend_schema(request=RegisterSerializer, responses={201: AuthResponseSerializer})
    def post(self, request):
        serializer = RegisterSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        return Response(_auth_payload(user, request), status=status.HTTP_201_CREATED)


class LoginView(PublicAuthView):
    throttle_scope = "auth_login"

    @extend_schema(request=LoginSerializer, responses={200: AuthResponseSerializer})
    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = services.login(request=request, **serializer.validated_data)
        return Response(_auth_payload(user, request))


class TokenRefreshView(SimpleJWTRefreshView):
    throttle_scope = "auth_token_refresh"


class LogoutView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(request=LogoutSerializer, responses={204: None})
    def post(self, request):
        serializer = LogoutSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            token = RefreshToken(serializer.validated_data["refresh"])
        except TokenError as exc:
            raise ValidationError({"refresh": ["Token is invalid or expired."]}) from exc
        if str(token.get("user_id")) != str(request.user.pk):
            raise ValidationError({"refresh": ["Token does not belong to this user."]})
        token.blacklist()
        return Response(status=status.HTTP_204_NO_CONTENT)


class MeView(generics.RetrieveUpdateAPIView):
    serializer_class = UserSerializer
    permission_classes = [IsAuthenticated]
    http_method_names = ["get", "patch", "head", "options"]

    def get_object(self):
        return self.request.user


class PasswordChangeView(APIView):
    permission_classes = [IsAuthenticated]
    throttle_scope = "auth_password_reset"

    @extend_schema(request=PasswordChangeSerializer, responses={200: TokenPairSerializer})
    def post(self, request):
        serializer = PasswordChangeSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        services.set_password(request.user, serializer.validated_data["new_password"])
        # Every old session is now revoked; hand this client a fresh pair.
        return Response({"tokens": services.issue_tokens(request.user)})


class PasswordResetRequestView(PublicAuthView):
    throttle_scope = "auth_password_reset"

    @extend_schema(request=PasswordResetRequestSerializer, responses={202: None})
    def post(self, request):
        serializer = PasswordResetRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        services.send_password_reset(serializer.validated_data["email"])
        # Same answer whether or not the account exists (no account enumeration).
        return Response(
            {"detail": "If an account exists for this email, a reset link has been sent."},
            status=status.HTTP_202_ACCEPTED,
        )


class PasswordResetConfirmView(PublicAuthView):
    throttle_scope = "auth_password_reset"

    @extend_schema(request=PasswordResetConfirmSerializer, responses={204: None})
    def post(self, request):
        serializer = PasswordResetConfirmSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        services.set_password(
            serializer.validated_data["user"], serializer.validated_data["new_password"]
        )
        return Response(status=status.HTTP_204_NO_CONTENT)


class VerifyEmailView(PublicAuthView):
    throttle_scope = "auth_password_reset"

    @extend_schema(request=VerifyEmailSerializer, responses={204: None})
    def post(self, request):
        serializer = VerifyEmailSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        if services.verify_email(serializer.validated_data["token"]) is None:
            raise ValidationError({"token": ["This link is invalid or has expired."]})
        return Response(status=status.HTTP_204_NO_CONTENT)


class ResendVerificationView(APIView):
    permission_classes = [IsAuthenticated]
    throttle_scope = "auth_password_reset"

    @extend_schema(request=None, responses={202: None})
    def post(self, request):
        if not request.user.email:
            raise ValidationError({"email": ["Add an email address first."]})
        services.send_email_verification(request.user)
        return Response(status=status.HTTP_202_ACCEPTED)


class SessionsView(APIView):
    """Signed-in browsers/devices, and signing out of all of them."""

    permission_classes = [IsAuthenticated]

    @extend_schema(responses=SessionSerializer(many=True))
    def get(self, request):
        return Response(SessionSerializer(services.active_sessions(request.user), many=True).data)

    @extend_schema(request=None, responses={204: None})
    def delete(self, request):
        services.revoke_refresh_tokens(request.user)
        return Response(status=status.HTTP_204_NO_CONTENT)


class AdminUserViewSet(AuditedViewSetMixin, viewsets.ModelViewSet):
    """Admin user management. DELETE deactivates the account; rows are never removed."""

    queryset = User.objects.all()
    serializer_class = AdminUserSerializer
    permission_classes = [IsAdmin, CanManageUser]
    http_method_names = ["get", "post", "patch", "delete", "head", "options"]
    filterset_fields = ["role", "is_active"]
    search_fields = ["full_name", "email", "phone"]
    ordering_fields = ["date_joined", "full_name", "last_login"]

    def perform_destroy(self, instance):
        if instance.pk == self.request.user.pk:
            raise ValidationError({"detail": ["You cannot deactivate your own account."]})
        services.deactivate_user(instance)
        record(actor=self.request.user, action="deactivate", obj=instance, request=self.request)
