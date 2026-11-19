from rest_framework import status
from rest_framework.exceptions import APIException


class BookingConflict(APIException):
    """The request is valid but the current state of the departure/booking forbids it."""

    status_code = status.HTTP_409_CONFLICT
    default_detail = "This booking action is not possible right now."
    default_code = "booking_conflict"

    def __init__(self, detail: str, code: str):
        super().__init__(detail=detail, code=code)
