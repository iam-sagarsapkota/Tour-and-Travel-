from .base import *

DEBUG = True
# Development-only fallback; production requires DJANGO_SECRET_KEY (see production.py).
SECRET_KEY = env("DJANGO_SECRET_KEY", default="dev-only-insecure-key-do-not-use-in-production")
ALLOWED_HOSTS = env.list("DJANGO_ALLOWED_HOSTS", default=["localhost", "127.0.0.1", "backend"])

if not env("EMAIL_BACKEND", default=""):
    # Print emails (e.g. password reset links) to the console unless a backend is configured.
    MAILERS = {"default": {"BACKEND": "django.core.mail.backends.console.EmailBackend"}}

CORS_ALLOWED_ORIGINS = env.list(
    "CORS_ALLOWED_ORIGINS", default=["http://localhost:5173", "http://127.0.0.1:5173"]
)
REST_FRAMEWORK["DEFAULT_RENDERER_CLASSES"] = [
    "rest_framework.renderers.JSONRenderer",
    "rest_framework.renderers.BrowsableAPIRenderer",
]

if not env("REDIS_URL", default=""):
    # Running outside Docker without Redis: keep throttling and caching in-process.
    CACHES = {"default": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache"}}

# eSewa's public sandbox (UAT) merchant from https://developer.esewa.com.np/pages/Epay.
# These are documented test values, not secrets. Real credentials come from the environment.
ESEWA_ENABLED = env.bool("ESEWA_ENABLED", default=True)
ESEWA_PRODUCT_CODE = env("ESEWA_PRODUCT_CODE", default="EPAYTEST")
ESEWA_SECRET_KEY = env("ESEWA_SECRET_KEY", default="8gBm/:&EnhH.1/q")
