"""Wording of every notification. Each builder returns a Message; rendering is shared."""

from dataclasses import dataclass, field

from django.conf import settings
from django.template.loader import render_to_string

from apps.bookings.models import Booking

from .models import Notification

Kind = Notification.Kind


@dataclass
class Message:
    subject: str
    heading: str
    paragraphs: list[str]
    details: list[tuple[str, str]] = field(default_factory=list)
    action_label: str = ""
    action_url: str = ""
    note: str = ""

    def render(self) -> tuple[str, str]:
        """Return (plain text, HTML). Template autoescaping protects the HTML version."""
        support = _support_email()
        context = {**self.__dict__, "support_email": support}
        html = render_to_string("notifications/email.html", context)
        lines = [self.heading, "", *self.paragraphs]
        if self.details:
            lines += ["", *(f"{label}: {value}" for label, value in self.details)]
        if self.action_url:
            lines += ["", f"{self.action_label}: {self.action_url}"]
        if self.note:
            lines += ["", self.note]
        lines += ["", "Himalaya Trails"]
        if support:
            lines.append(f"Questions? Write to {support}.")
        return "\n".join(lines), html


def _support_email() -> str:
    from apps.operations.models import SiteSettings  # avoid import cycle at load time

    return SiteSettings.load().support_email


def _url(path: str) -> str:
    return f"{settings.FRONTEND_URL.rstrip('/')}{path}"


def _money(amount, currency) -> str:
    return f"{currency} {amount:,.2f}".replace(".00", "")


def _trip_details(booking: Booking) -> list[tuple[str, str]]:
    departure = booking.departure
    return [
        ("Booking reference", booking.reference),
        ("Trip", departure.adventure.title),
        ("Dates", f"{departure.start_date:%d %b %Y} - {departure.end_date:%d %b %Y}"),
        ("Travellers", str(booking.participant_count)),
        ("Total", _money(booking.total_amount, booking.currency)),
    ]


def _booking_link(booking: Booking) -> str:
    return _url(f"/dashboard/bookings/{booking.pk}")


def welcome(user, **_) -> Message:
    return Message(
        subject="Welcome to Himalaya Trails",
        heading=f"Namaste, {user.get_short_name() or 'trekker'}!",
        paragraphs=[
            "Your account is ready. You can now see full trip details, book places on "
            "scheduled departures and pay online with eSewa or Khalti.",
        ],
        action_label="Find your trail",
        action_url=_url("/events"),
    )


def email_verification(user, *, link: str, **_) -> Message:
    return Message(
        subject="Confirm your email address",
        heading="Confirm your email",
        paragraphs=[
            "Please confirm this is your email address so we can reach you about your trips."
        ],
        action_label="Confirm email",
        action_url=link,
        note="The link expires in 3 days. If you didn't create an account, ignore this email.",
    )


def password_reset(user, *, link: str, minutes: int, **_) -> Message:
    return Message(
        subject="Reset your Himalaya Trails password",
        heading="Reset your password",
        paragraphs=[f"Hello {user.full_name}, use the button below to choose a new password."],
        action_label="Choose a new password",
        action_url=link,
        note=f"The link expires in {minutes} minutes and works once. "
        "If you didn't ask for this, you can ignore this email.",
    )


def booking_confirmed(user, *, booking: Booking, **_) -> Message:
    payment = getattr(booking, "payment", None)
    details = _trip_details(booking)
    if payment and payment.provider:
        details.append(("Paid with", payment.get_provider_display()))
        if payment.gateway_reference:
            details.append(("Payment reference", payment.gateway_reference))
    return Message(
        subject=f"Booking confirmed: {booking.departure.adventure.title}",
        heading="You're booked!",
        paragraphs=[
            "Thank you. Your payment was received and your places are confirmed. "
            "Keep this email as your receipt.",
        ],
        details=details,
        action_label="View your booking",
        action_url=_booking_link(booking),
        note=booking.departure.adventure.cancellation_policy,
    )


def payment_failed(user, *, booking: Booking, **_) -> Message:
    return Message(
        subject="Your payment didn't go through",
        heading="Payment not completed",
        paragraphs=[
            "We couldn't confirm your payment for this booking. If your places are still "
            "held you can try again from your booking page.",
        ],
        details=_trip_details(booking),
        action_label="Try again",
        action_url=_booking_link(booking),
    )


def payment_needs_review(user, *, booking: Booking, **_) -> Message:
    return Message(
        subject="We're reviewing your payment",
        heading="We received your payment",
        paragraphs=[
            "Your payment arrived, but we couldn't confirm your places automatically "
            "(the hold had ended and the departure filled up, or the booking had changed). "
            "Our team will contact you and refund you if the trip can't go ahead.",
        ],
        details=_trip_details(booking),
        action_label="View your booking",
        action_url=_booking_link(booking),
    )


def booking_cancelled(user, *, booking: Booking, **_) -> Message:
    paragraphs = ["Your booking has been cancelled and the places released."]
    if booking.cancellation_reason:
        paragraphs.append(f"Reason: {booking.cancellation_reason}")
    if getattr(booking, "payment", None) and booking.payment.status == "successful":
        paragraphs.append("You paid for this booking; our team will be in touch about a refund.")
    return Message(
        subject=f"Booking cancelled: {booking.departure.adventure.title}",
        heading="Booking cancelled",
        paragraphs=paragraphs,
        details=_trip_details(booking),
        action_label="Find another trip",
        action_url=_url("/events"),
    )


def booking_expired(user, *, booking: Booking, **_) -> Message:
    return Message(
        subject="Your seat hold has ended",
        heading="Your places were released",
        paragraphs=[
            "We didn't receive payment before the hold ended, so the places went back on "
            "sale. You can book again if the departure still has room.",
        ],
        details=_trip_details(booking),
        action_label="See the trip",
        action_url=_url(f"/events/{booking.departure.adventure.slug}"),
    )


def departure_changed(user, *, booking: Booking, changes: list[str], **_) -> Message:
    return Message(
        subject=f"Change to your trip: {booking.departure.adventure.title}",
        heading="Your departure has changed",
        paragraphs=["The organiser has updated your departure:", *changes],
        details=_trip_details(booking),
        action_label="View your booking",
        action_url=_booking_link(booking),
        note="If the new arrangements don't work for you, reply to this email.",
    )


def trip_reminder(user, *, booking: Booking, **_) -> Message:
    adventure = booking.departure.adventure
    paragraphs = [f"Your trip starts on {booking.departure.start_date:%A %d %B}. Time to pack!"]
    if adventure.meeting_point:
        paragraphs.append(f"Meeting point: {adventure.meeting_point}")
    if adventure.equipment:
        paragraphs.append(f"Bring: {adventure.equipment}")
    return Message(
        subject=f"Your trip is coming up: {adventure.title}",
        heading="Your adventure is almost here",
        paragraphs=paragraphs,
        details=_trip_details(booking),
        action_label="View trip details",
        action_url=_booking_link(booking),
    )


BUILDERS = {
    Kind.WELCOME: welcome,
    Kind.EMAIL_VERIFICATION: email_verification,
    Kind.PASSWORD_RESET: password_reset,
    Kind.BOOKING_CONFIRMED: booking_confirmed,
    Kind.PAYMENT_FAILED: payment_failed,
    Kind.PAYMENT_NEEDS_REVIEW: payment_needs_review,
    Kind.BOOKING_CANCELLED: booking_cancelled,
    Kind.BOOKING_EXPIRED: booking_expired,
    Kind.DEPARTURE_CHANGED: departure_changed,
    Kind.TRIP_REMINDER: trip_reminder,
}
