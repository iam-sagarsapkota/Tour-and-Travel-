import datetime as dt
import re
import smtplib

import pytest
from django.core import mail
from django.urls import reverse
from django.utils import timezone

from apps.bookings import services as booking_services
from apps.notifications import services
from apps.notifications.models import Notification

pytestmark = pytest.mark.django_db
Kind = Notification.Kind


def book(user, departure, count=1, **kwargs):
    return booking_services.create_booking(
        user=user,
        departure_id=departure.pk,
        participants=[{"full_name": f"P{n}"} for n in range(count)],
        policy_accepted=True,
        **kwargs,
    )


def kinds(user):
    return sorted(Notification.objects.filter(user=user).values_list("kind", flat=True))


class TestAccountEmails:
    def test_registration_sends_welcome_and_verification(self, api):
        api.post(
            reverse("auth:register"),
            {
                "full_name": "Maya Gurung",
                "email": "maya@example.com",
                "password": "Trek-Safely-2026",
                "password_confirm": "Trek-Safely-2026",
            },
        )
        subjects = sorted(message.subject for message in mail.outbox)
        assert subjects == ["Confirm your email address", "Welcome to Himalaya Trails"]
        welcome = next(m for m in mail.outbox if m.subject.startswith("Welcome"))
        assert welcome.to == ["maya@example.com"]
        assert welcome.alternatives[0][1] == "text/html"  # branded HTML version

    def test_phone_only_account_is_kept_in_app_but_not_emailed(self, api):
        api.post(
            reverse("auth:register"),
            {
                "full_name": "Dawa Lama",
                "phone": "9812345678",
                "password": "Trek-Safely-2026",
                "password_confirm": "Trek-Safely-2026",
            },
        )
        assert mail.outbox == []
        notification = Notification.objects.get(kind=Kind.WELCOME)
        assert notification.status == Notification.Status.SKIPPED

    def test_sensitive_links_are_redacted_after_sending(self, user):
        services.notify(
            user, Kind.PASSWORD_RESET, link="https://x.test/reset?token=SECRET", minutes=60
        )

        assert "SECRET" in mail.outbox[0].body
        stored = Notification.objects.get(kind=Kind.PASSWORD_RESET)
        assert stored.status == Notification.Status.SENT
        assert "SECRET" not in stored.body_text + stored.body_html


class TestEmailVerification:
    def _link_token(self):
        message = next(m for m in mail.outbox if "Confirm" in m.subject)
        return re.search(r"verify-email\?token=(\S+)", message.body).group(1)

    def test_verify_link_marks_address_verified(self, api, user):
        from apps.accounts.services import send_email_verification

        send_email_verification(user)
        response = api.post(reverse("auth:verify-email"), {"token": self._link_token()})

        assert response.status_code == 204
        user.refresh_from_db()
        assert user.email_verified

    def test_link_dies_if_email_changes(self, api, user):
        from apps.accounts.services import send_email_verification

        send_email_verification(user)
        token = self._link_token()
        user.email = "new@example.com"
        user.save()

        assert api.post(reverse("auth:verify-email"), {"token": token}).status_code == 400

    def test_tampered_token_rejected(self, api):
        assert api.post(reverse("auth:verify-email"), {"token": "abc:def"}).status_code == 400

    def test_resend(self, auth_client, user):
        response = auth_client(user).post(reverse("auth:verify-email-resend"))
        assert response.status_code == 202
        assert any("Confirm" in m.subject for m in mail.outbox)


class TestBookingEmails:
    def test_confirmation_is_sent_once(self, user, make_departure):
        booking = book(user, make_departure())
        booking_services.confirm_booking(booking)
        booking_services.confirm_booking(booking)  # repeated callback

        confirmations = [m for m in mail.outbox if m.subject.startswith("Booking confirmed")]
        assert len(confirmations) == 1
        assert booking.reference in confirmations[0].body
        assert f"/dashboard/bookings/{booking.pk}" in confirmations[0].body

    def test_cancellation_email_includes_reason(self, user, admin_user, make_departure):
        booking = book(user, make_departure())
        booking_services.cancel_booking(
            booking, actor=admin_user, reason="Trail closed by landslide"
        )
        message = next(m for m in mail.outbox if m.subject.startswith("Booking cancelled"))
        assert "Trail closed by landslide" in message.body

    def test_expired_hold_email(self, user, make_departure):
        book(user, make_departure(), now=timezone.now() - dt.timedelta(hours=1))
        booking_services.expire_pending_bookings()
        assert Kind.BOOKING_EXPIRED in kinds(user)

    def test_no_expiry_email_while_payment_in_flight(self, user, make_departure):
        from apps.payments.models import Payment

        booking = book(user, make_departure(), now=timezone.now() - dt.timedelta(hours=1))
        Payment.objects.create(
            booking=booking, amount=booking.total_amount, currency="NPR", status="processing"
        )
        booking_services.expire_pending_bookings()
        assert Kind.BOOKING_EXPIRED not in kinds(user)

    def test_departure_change_notifies_holding_travellers(
        self, auth_client, admin_user, user, make_user, make_departure
    ):
        departure = make_departure(days_ahead=40)
        booking = book(user, departure)
        cancelled = book(make_user(), departure)
        booking_services.cancel_booking(cancelled, actor=cancelled.user)
        url = reverse("catalog_admin:departure-detail", args=[departure.pk])
        new_start = (timezone.localdate() + dt.timedelta(days=45)).isoformat()

        auth_client(admin_user).patch(url, {"start_date": new_start, "end_date": new_start})

        changed = Notification.objects.filter(kind=Kind.DEPARTURE_CHANGED)
        assert [n.booking_id for n in changed] == [booking.pk]
        assert "New dates" in changed.get().body_text

    def test_unrelated_departure_edit_sends_nothing(
        self, auth_client, admin_user, user, make_departure
    ):
        departure = make_departure()
        book(user, departure)
        url = reverse("catalog_admin:departure-detail", args=[departure.pk])
        auth_client(admin_user).patch(url, {"capacity": 30})
        assert not Notification.objects.filter(kind=Kind.DEPARTURE_CHANGED).exists()


class TestTripReminders:
    def test_reminds_confirmed_trips_once_and_respects_opt_out(
        self, user, make_user, make_departure, settings
    ):
        settings.TRIP_REMINDER_DAYS = 3
        departure = make_departure(days_ahead=3)
        departure.booking_cutoff = timezone.now() + dt.timedelta(hours=1)
        departure.save()
        mine = book(user, departure)
        booking_services.confirm_booking(mine)
        quiet = make_user()
        quiet.profile.trip_reminders = False
        quiet.profile.save()
        booking_services.confirm_booking(book(quiet, departure))
        book(make_user(), departure)  # unpaid: no reminder

        assert services.send_trip_reminders() == 1
        assert services.send_trip_reminders() == 0  # deduplicated
        reminder = Notification.objects.get(kind=Kind.TRIP_REMINDER)
        assert reminder.booking_id == mine.pk


class TestDelivery:
    def test_transient_failure_is_retried_then_marked_failed(self, user, monkeypatch):
        monkeypatch.setattr(services, "_after_commit", lambda callback: None)  # don't send yet
        notification = services.notify(user, Kind.WELCOME)

        def broken(self, *args, **kwargs):
            raise smtplib.SMTPServerDisconnected("mail server went away")

        monkeypatch.setattr("django.core.mail.EmailMultiAlternatives.send", broken)
        with pytest.raises(smtplib.SMTPServerDisconnected):
            services.deliver(notification.pk)
        notification.refresh_from_db()
        assert (notification.status, notification.attempts) == ("queued", 1)

        services.mark_failed(notification.pk, "Gave up after retries")
        notification.refresh_from_db()
        assert notification.status == Notification.Status.FAILED

    def test_delivery_is_idempotent(self, user):
        notification = services.notify(user, Kind.WELCOME)
        assert services.deliver(notification.pk) == "sent"
        assert len(mail.outbox) == 1

    def test_duplicate_events_create_one_notification(self, user):
        assert services.notify(user, Kind.WELCOME, dedupe_key="k1")
        assert services.notify(user, Kind.WELCOME, dedupe_key="k1") is None
        assert Notification.objects.count() == 1


class TestInAppList:
    def test_lists_own_notifications_and_hides_sensitive_bodies(self, auth_client, user, make_user):
        services.notify(user, Kind.WELCOME)
        services.notify(user, Kind.PASSWORD_RESET, link="https://x.test/r?token=SECRET", minutes=60)
        services.notify(make_user(), Kind.WELCOME)
        client = auth_client(user)

        rows = client.get(reverse("notifications")).data["results"]

        assert {row["kind"] for row in rows} == {"welcome", "password_reset"}
        reset = next(row for row in rows if row["kind"] == "password_reset")
        assert reset["body"] == ""

        assert client.post(reverse("notifications-read-all")).data == {"marked_read": 2}
        assert all(row["read_at"] for row in client.get(reverse("notifications")).data["results"])


class TestTasks:
    def _queued(self, user, monkeypatch):
        monkeypatch.setattr(services, "_after_commit", lambda callback: None)
        return services.notify(user, Kind.WELCOME)

    def test_gives_up_after_max_retries(self, user, monkeypatch):
        from apps.notifications.tasks import send_notification_task

        notification = self._queued(user, monkeypatch)

        def broken(self, *args, **kwargs):
            raise smtplib.SMTPServerDisconnected("down")

        monkeypatch.setattr("django.core.mail.EmailMultiAlternatives.send", broken)
        result = send_notification_task.apply(args=[str(notification.pk)], retries=5)

        assert result.get() == "failed"
        notification.refresh_from_db()
        assert notification.status == Notification.Status.FAILED
        assert "Gave up" in notification.last_error

    def test_non_transient_error_is_not_retried(self, user, monkeypatch):
        from apps.notifications.tasks import send_notification_task

        notification = self._queued(user, monkeypatch)

        def bad(self, *args, **kwargs):
            raise ValueError("bad header")

        monkeypatch.setattr("django.core.mail.EmailMultiAlternatives.send", bad)
        assert send_notification_task.apply(args=[str(notification.pk)]).get() == "failed"

    def test_reminder_task(self):
        from apps.notifications.tasks import send_trip_reminders_task

        assert send_trip_reminders_task.delay().get() == 0
