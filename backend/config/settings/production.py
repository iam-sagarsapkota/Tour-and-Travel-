from django.core.exceptions import ImproperlyConfigured

from .base import *

DEBUG = False
SECRET_KEY = env("DJANGO_SECRET_KEY")  # required; no default
ALLOWED_HOSTS = env.list("DJANGO_ALLOWED_HOSTS")  # required

SECURE_SSL_REDIRECT = env.bool("SECURE_SSL_REDIRECT", default=True)
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
SECURE_HSTS_SECONDS = env.int("SECURE_HSTS_SECONDS", default=31536000)
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_REFERRER_POLICY = "same-origin"
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SESSION_COOKIE_HTTPONLY = True
X_FRAME_OPTIONS = "DENY"

# Refuse to take real bookings against payment sandboxes.
if ESEWA_ENABLED and (ESEWA_PRODUCT_CODE == "EPAYTEST" or "rc-epay" in ESEWA_FORM_URL):
    raise ImproperlyConfigured("eSewa is configured with sandbox credentials or URLs.")
if KHALTI_SECRET_KEY and "dev.khalti.com" in KHALTI_BASE_URL:
    raise ImproperlyConfigured("Khalti is pointed at the sandbox (KHALTI_BASE_URL).")
