from django.db import connection
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView


class HealthView(APIView):
    """Liveness: the process is up."""

    authentication_classes = []
    permission_classes = [AllowAny]
    throttle_classes = []
    schema = None

    def get(self, request):
        return Response({"status": "ok"})


class ReadinessView(HealthView):
    """Readiness: the database answers."""

    def get(self, request):
        try:
            with connection.cursor() as cursor:
                cursor.execute("SELECT 1")
        except Exception:  # any DB failure means not ready
            return Response({"status": "unavailable"}, status=503)
        return Response({"status": "ok"})
