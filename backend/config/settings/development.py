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
