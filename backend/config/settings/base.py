"""Settings shared by every environment. Secrets come from the environment only."""

from datetime import timedelta
from pathlib import Path

import environ

BASE_DIR = Path(__file__).resolve().parent.parent.parent

env = environ.Env()
# Optional local .env (repo root). In Docker/production, real env vars are injected instead.
_env_file = BASE_DIR.parent / ".env"
if _env_file.exists():
    env.read_env(_env_file)

DEBUG = False
ALLOWED_HOSTS = env.list("DJANGO_ALLOWED_HOSTS", default=[])

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    # Third party
    "rest_framework",
    "rest_framework_simplejwt.token_blacklist",
    "corsheaders",
    "django_filters",
    "drf_spectacular",
    # Local
    "common",
    "apps.accounts",
    "apps.destinations",
    "apps.adventures",
    "apps.departures",
    "apps.bookings",
    "apps.payments",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "corsheaders.middleware.CorsMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"
WSGI_APPLICATION = "config.wsgi.application"
ASGI_APPLICATION = "config.asgi.application"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

# --- Database -------------------------------------------------------------
DATABASES = {
    "default": env.db(
        "DATABASE_URL",
        default="postgres://tour_travel:tour_travel@localhost:5432/tour_travel",
    )
}
DATABASES["default"]["CONN_MAX_AGE"] = env.int("DATABASE_CONN_MAX_AGE", default=60)
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# --- Identity / auth ------------------------------------------------------
AUTH_USER_MODEL = "accounts.User"
AUTHENTICATION_BACKENDS = ["apps.accounts.backends.EmailOrPhoneBackend"]
AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator",
        "OPTIONS": {"user_attributes": ("full_name", "email", "phone")},
    },
    {
        "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
        "OPTIONS": {"min_length": 8},
    },
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]
PASSWORD_RESET_TIMEOUT = 60 * 60  # seconds a reset link stays valid

# --- I18n / time ----------------------------------------------------------
LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"  # store UTC; present Asia/Kathmandu in clients/reports
USE_I18N = True
USE_TZ = True

# --- Static / media -------------------------------------------------------
STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
MEDIA_URL = "media/"
MEDIA_ROOT = BASE_DIR / "media"
MAX_IMAGE_UPLOAD_BYTES = env.int("MAX_IMAGE_UPLOAD_BYTES", default=5 * 1024 * 1024)

# --- Business rules -------------------------------------------------------
# Trips run on Nepal time; dates such as booking cutoffs are derived in this zone.
BUSINESS_TIME_ZONE = "Asia/Kathmandu"
# Used when an admin schedules a departure without an explicit booking cutoff.
DEFAULT_BOOKING_CUTOFF_DAYS = env.int("DEFAULT_BOOKING_CUTOFF_DAYS", default=3)
# How long unpaid seats are held before they return to sale (product decision: 15 min).
BOOKING_HOLD_MINUTES = env.int("BOOKING_HOLD_MINUTES", default=15)
MAX_PARTICIPANTS_PER_BOOKING = env.int("MAX_PARTICIPANTS_PER_BOOKING", default=20)

# --- Payments -------------------------------------------------------------
# Starting a payment extends the seat hold so the traveller can finish checkout.
PAYMENT_HOLD_MINUTES = env.int("PAYMENT_HOLD_MINUTES", default=20)
# A gateway "expired/not found" answer is not final before this age (user may still pay).
PAYMENT_ATTEMPT_GRACE_MINUTES = env.int("PAYMENT_ATTEMPT_GRACE_MINUTES", default=30)
PAYMENT_HTTP_TIMEOUT = env.int("PAYMENT_HTTP_TIMEOUT", default=15)
# eSewa ePay v2. Defaults are the documented sandbox (UAT) URLs; credentials must be set.
ESEWA_ENABLED = env.bool("ESEWA_ENABLED", default=False)
ESEWA_PRODUCT_CODE = env("ESEWA_PRODUCT_CODE", default="")
ESEWA_SECRET_KEY = env("ESEWA_SECRET_KEY", default="")
ESEWA_FORM_URL = env("ESEWA_FORM_URL", default="https://rc-epay.esewa.com.np/api/epay/main/v2/form")
ESEWA_STATUS_URL = env(
    "ESEWA_STATUS_URL", default="https://rc.esewa.com.np/api/epay/transaction/status/"
)
# Khalti KPG-2. Enabled when a secret key is set (sandbox key from test-admin.khalti.com).
KHALTI_SECRET_KEY = env("KHALTI_SECRET_KEY", default="")
KHALTI_BASE_URL = env("KHALTI_BASE_URL", default="https://dev.khalti.com/api/v2/")

# --- Cache / Celery -------------------------------------------------------
REDIS_URL = env("REDIS_URL", default="redis://localhost:6379/0")
CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.redis.RedisCache",
        "LOCATION": REDIS_URL,
    }
}
CELERY_BROKER_URL = env("CELERY_BROKER_URL", default=REDIS_URL)
CELERY_RESULT_BACKEND = env("CELERY_RESULT_BACKEND", default=REDIS_URL)
CELERY_TASK_ACKS_LATE = True
CELERY_TIMEZONE = TIME_ZONE
CELERY_BEAT_SCHEDULE = {
    "expire-unpaid-booking-holds": {
        "task": "bookings.expire_pending_bookings",
        "schedule": 60.0,  # seconds
    },
    "reconcile-open-payments": {
        "task": "payments.reconcile_open_attempts",
        "schedule": 300.0,  # eSewa: use the status API if no answer within five minutes
    },
}

# --- Email ----------------------------------------------------------------
# Django 6.1 MAILERS configuration. SMTP options are only read when SMTP is the backend.
EMAIL_BACKEND_PATH = (
    env("EMAIL_BACKEND", default="") or "django.core.mail.backends.smtp.EmailBackend"
)
MAILERS = {"default": {"BACKEND": EMAIL_BACKEND_PATH}}
if EMAIL_BACKEND_PATH.endswith("smtp.EmailBackend"):
    MAILERS["default"]["OPTIONS"] = {
        "host": env("EMAIL_HOST", default="localhost"),
        "port": env.int("EMAIL_PORT", default=587),
        "username": env("EMAIL_HOST_USER", default=""),
        "password": env("EMAIL_HOST_PASSWORD", default=""),
        "use_tls": env.bool("EMAIL_USE_TLS", default=True),
    }
DEFAULT_FROM_EMAIL = env("DEFAULT_FROM_EMAIL", default="Himalaya Trails <no-reply@localhost>")

# Used to build links in emails (password reset, verification).
FRONTEND_URL = env("FRONTEND_URL", default="http://localhost:5173")

# --- CORS / CSRF ----------------------------------------------------------
CORS_ALLOWED_ORIGINS = env.list("CORS_ALLOWED_ORIGINS", default=[])
CSRF_TRUSTED_ORIGINS = env.list("CSRF_TRUSTED_ORIGINS", default=[])

# --- DRF ------------------------------------------------------------------
REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "rest_framework_simplejwt.authentication.JWTAuthentication",
    ],
    # Deny by default: public endpoints must opt in with AllowAny.
    "DEFAULT_PERMISSION_CLASSES": ["rest_framework.permissions.IsAuthenticated"],
    "DEFAULT_RENDERER_CLASSES": ["rest_framework.renderers.JSONRenderer"],
    "DEFAULT_PARSER_CLASSES": ["rest_framework.parsers.JSONParser"],
    "DEFAULT_FILTER_BACKENDS": [
        "django_filters.rest_framework.DjangoFilterBackend",
        "rest_framework.filters.SearchFilter",
        "rest_framework.filters.OrderingFilter",
    ],
    "DEFAULT_PAGINATION_CLASS": "common.pagination.StandardPagination",
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
    "EXCEPTION_HANDLER": "common.exceptions.api_exception_handler",
    "TEST_REQUEST_DEFAULT_FORMAT": "json",
    "DEFAULT_THROTTLE_CLASSES": [
        "rest_framework.throttling.AnonRateThrottle",
        "rest_framework.throttling.UserRateThrottle",
        "rest_framework.throttling.ScopedRateThrottle",
    ],
    "DEFAULT_THROTTLE_RATES": {
        "anon": "120/min",
        "user": "600/min",
        "auth_login": "10/min",
        "auth_register": "20/hour",
        "auth_password_reset": "5/hour",
        "auth_token_refresh": "60/min",
        "bookings_create": "30/hour",
        "payments": "60/hour",
    },
}

SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(minutes=env.int("JWT_ACCESS_MINUTES", default=15)),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=env.int("JWT_REFRESH_DAYS", default=7)),
    "ROTATE_REFRESH_TOKENS": True,
    "BLACKLIST_AFTER_ROTATION": True,
    "UPDATE_LAST_LOGIN": False,
    # Embeds a hash of the password in each token so a password change
    # invalidates every previously issued access/refresh token.
    "CHECK_REVOKE_TOKEN": True,
    "AUTH_HEADER_TYPES": ("Bearer",),
}

SPECTACULAR_SETTINGS = {
    "TITLE": "Himalaya Trails API",
    "DESCRIPTION": "Tour & Travel System - Nepal trekking and hiking booking platform.",
    "VERSION": "1.0.0",
    "SERVE_INCLUDE_SCHEMA": False,
    "SCHEMA_PATH_PREFIX": "/api/v1",
    # Two different "status" choice sets exist; give each a stable schema name.
    "ENUM_NAME_OVERRIDES": {
        "PublishStatusEnum": "common.models.PublishStatus",
        "DepartureStatusEnum": "apps.departures.models.DepartureStatus",
        "BookingStatusEnum": "apps.bookings.models.BookingStatus",
        "PaymentStatusEnum": "apps.payments.models.PaymentStatus",
        "PaymentAttemptStatusEnum": "apps.payments.models.PaymentAttemptStatus",
    },
}

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "standard": {"format": "%(asctime)s %(levelname)s %(name)s %(message)s"},
    },
    "handlers": {"console": {"class": "logging.StreamHandler", "formatter": "standard"}},
    "root": {"handlers": ["console"], "level": env("LOG_LEVEL", default="INFO")},
}
