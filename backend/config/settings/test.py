from .base import *

DEBUG = False
SECRET_KEY = "test-only-secret-key-not-used-anywhere-else-0123456789"
ALLOWED_HOSTS = ["testserver", "localhost"]

# CI and Docker set DATABASE_URL to PostgreSQL. Without it, tests fall back to
# in-memory SQLite so the suite can run on a machine with no database server.
DATABASES = {"default": env.db("DATABASE_URL", default="sqlite://:memory:")}

PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]
MAILERS = {"default": {"BACKEND": "django.core.mail.backends.locmem.EmailBackend"}}
CACHES = {"default": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache"}}
CELERY_TASK_ALWAYS_EAGER = True
CELERY_TASK_EAGER_PROPAGATES = True
