"""Load demo catalog data for local development.

    python manage.py seed_catalog

Safe to run repeatedly: rows are matched by slug and updated. Prices, dates and
logistics are illustrative placeholders, not real offers.
"""

import datetime as dt

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone

from apps.adventures.models import Adventure, AdventureCategory, ItineraryDay
from apps.departures.models import Departure
from apps.departures.serializers import start_of_day
from apps.destinations.models import Destination
from common.models import PublishStatus

PERMIT_NOTE = (
    "Permit rules and fees change. Confirm current requirements with the Nepal Tourism "
    "Board (https://ntb.gov.np) and the Department of National Parks and Wildlife "
    "Conservation (https://dnpwc.gov.np) before travelling."
)

DESTINATIONS = [
    {
        "slug": "everest",
        "name": "Everest Region",
        "region": "Koshi",
        "short_description": "The Khumbu valleys beneath the world's highest peak.",
        "best_season": "March-May, late September-November",
        "permit_info": "Sagarmatha National Park entry permit and a local municipality "
        "permit are normally required. " + PERMIT_NOTE,
    },
    {
        "slug": "annapurna",
        "name": "Annapurna Region",
        "region": "Gandaki",
        "short_description": "Classic teahouse trails through rhododendron forest to "
        "high mountain amphitheatres.",
        "best_season": "March-May, October-November",
        "permit_info": "Annapurna Conservation Area Permit (ACAP) is normally required. "
        + PERMIT_NOTE,
    },
    {
        "slug": "langtang",
        "name": "Langtang Region",
        "region": "Bagmati",
        "short_description": "A glacial valley of Tamang villages close to Kathmandu.",
        "best_season": "March-May, October-November",
        "permit_info": "Langtang National Park entry permit is normally required. " + PERMIT_NOTE,
    },
    {
        "slug": "kathmandu-valley",
        "name": "Kathmandu Valley",
        "region": "Bagmati",
        "short_description": "Forested rim hikes and heritage towns around the capital.",
        "best_season": "October-April",
        "permit_info": "Shivapuri Nagarjun National Park charges an entry fee for hikes "
        "inside the park. " + PERMIT_NOTE,
    },
]

CATEGORIES = [
    {"slug": "teahouse-treks", "name": "Teahouse Treks"},
    {"slug": "short-treks", "name": "Short Treks"},
    {"slug": "day-hikes", "name": "Day Hikes"},
]

STANDARD_INCLUSIONS = ["Licensed guide", "Required permits", "Accommodation on the trail"]
STANDARD_EXCLUSIONS = ["International flights", "Travel insurance", "Personal equipment"]
POLICY = (
    "Demo policy: full refund up to 14 days before departure, 50% up to 7 days, "
    "no refund afterwards."
)

ADVENTURES = [
    {
        "slug": "everest-base-camp-trek",
        "title": "Everest Base Camp Trek",
        "destination": "everest",
        "category": "teahouse-treks",
        "activity_type": "trekking",
        "difficulty": "difficult",
        "duration_days": 14,
        "distance_km": "130",
        "max_elevation_m": 5545,
        "start_point": "Lukla",
        "end_point": "Lukla",
        "base_price": "185000",
        "is_featured": True,
        "summary": "Walk through Sherpa country to the foot of Everest and the "
        "Kala Patthar viewpoint.",
        "itinerary": ["Fly to Lukla, trek to Phakding", "Phakding to Namche Bazaar"],
        "departures": [(45, 12), (75, 12), (120, 10)],
    },
    {
        "slug": "annapurna-base-camp-trek",
        "title": "Annapurna Base Camp Trek",
        "destination": "annapurna",
        "category": "teahouse-treks",
        "activity_type": "trekking",
        "difficulty": "moderate",
        "duration_days": 10,
        "distance_km": "110",
        "max_elevation_m": 4130,
        "start_point": "Nayapul",
        "end_point": "Pokhara",
        "base_price": "95000",
        "is_featured": True,
        "summary": "Climb through terraced villages into the Annapurna Sanctuary.",
        "itinerary": ["Pokhara to Ghandruk", "Ghandruk to Chhomrong"],
        "departures": [(30, 14), (60, 14)],
    },
    {
        "slug": "poon-hill-trek",
        "title": "Ghorepani Poon Hill Trek",
        "destination": "annapurna",
        "category": "short-treks",
        "activity_type": "trekking",
        "difficulty": "easy",
        "duration_days": 4,
        "distance_km": "40",
        "max_elevation_m": 3210,
        "start_point": "Nayapul",
        "end_point": "Nayapul",
        "base_price": "38000",
        "summary": "A short trek to a famous sunrise viewpoint over Dhaulagiri and Annapurna.",
        "itinerary": ["Nayapul to Tikhedhunga", "Tikhedhunga to Ghorepani"],
        "departures": [(20, 16), (35, 16), (50, 16)],
    },
    {
        "slug": "langtang-valley-trek",
        "title": "Langtang Valley Trek",
        "destination": "langtang",
        "category": "teahouse-treks",
        "activity_type": "trekking",
        "difficulty": "moderate",
        "duration_days": 8,
        "distance_km": "65",
        "max_elevation_m": 3870,
        "start_point": "Syabrubesi",
        "end_point": "Syabrubesi",
        "base_price": "68000",
        "summary": "Follow the Langtang Khola to Kyanjin Gompa beneath Langtang Lirung.",
        "itinerary": ["Kathmandu to Syabrubesi", "Syabrubesi to Lama Hotel"],
        "departures": [(40, 12)],
    },
    {
        "slug": "shivapuri-day-hike",
        "title": "Shivapuri Peak Day Hike",
        "destination": "kathmandu-valley",
        "category": "day-hikes",
        "activity_type": "hiking",
        "difficulty": "easy",
        "duration_days": 1,
        "distance_km": "16",
        "max_elevation_m": 2732,
        "start_point": "Budhanilkantha",
        "end_point": "Budhanilkantha",
        "base_price": "4500",
        "summary": "A forest climb to the second-highest point on the valley rim.",
        "itinerary": ["Budhanilkantha to Shivapuri Peak and back"],
        "departures": [(10, 20), (17, 20), (24, 20)],
    },
    {
        # Priced inside the payment sandboxes' limits (Khalti test: NPR 10-200) so the
        # whole booking-and-payment flow can be tried with test wallets.
        "slug": "sandbox-payment-test-walk",
        "title": "Sandbox Payment Test Walk (demo)",
        "destination": "kathmandu-valley",
        "category": "day-hikes",
        "activity_type": "hiking",
        "difficulty": "easy",
        "duration_days": 1,
        "distance_km": "3",
        "max_elevation_m": 1400,
        "start_point": "Kathmandu",
        "end_point": "Kathmandu",
        "base_price": "100",
        "summary": "Demo listing for testing eSewa and Khalti sandbox payments. Not a real trip.",
        "itinerary": ["Short demo walk"],
        "departures": [(7, 50), (14, 50)],
    },
]


class Command(BaseCommand):
    help = "Create or update demo destinations, categories, adventures and departures."

    @transaction.atomic
    def handle(self, *args, **options):
        if not settings.DEBUG:
            raise CommandError("seed_catalog loads demo data and only runs with DEBUG=True.")

        destinations = {}
        for order, data in enumerate(DESTINATIONS, start=1):
            destinations[data["slug"]], _ = Destination.objects.update_or_create(
                slug=data["slug"],
                defaults={**data, "status": PublishStatus.PUBLISHED, "display_order": order},
            )

        categories = {}
        for order, data in enumerate(CATEGORIES, start=1):
            categories[data["slug"]], _ = AdventureCategory.objects.update_or_create(
                slug=data["slug"], defaults={**data, "display_order": order}
            )

        today = timezone.localdate()
        for data in ADVENTURES:
            data = dict(data)
            itinerary = data.pop("itinerary")
            departures = data.pop("departures")
            adventure, _ = Adventure.objects.update_or_create(
                slug=data["slug"],
                defaults={
                    **data,
                    "destination": destinations[data["destination"]],
                    "category": categories[data["category"]],
                    "description": data["summary"],
                    "inclusions": STANDARD_INCLUSIONS,
                    "exclusions": STANDARD_EXCLUSIONS,
                    "cancellation_policy": POLICY,
                    "organizer": "Himalaya Trails (demo)",
                    "status": PublishStatus.PUBLISHED,
                    "published_at": timezone.now(),
                },
            )
            adventure.itinerary.all().delete()
            ItineraryDay.objects.bulk_create(
                ItineraryDay(adventure=adventure, day_number=number, title=title)
                for number, title in enumerate(itinerary, start=1)
            )
            # Only add departures the first time, so reruns do not disturb bookings.
            if not adventure.departures.exists():
                for days_ahead, capacity in departures:
                    start = today + dt.timedelta(days=days_ahead)
                    Departure.objects.create(
                        adventure=adventure,
                        start_date=start,
                        end_date=start + dt.timedelta(days=adventure.duration_days - 1),
                        booking_cutoff=start_of_day(start)
                        - dt.timedelta(days=settings.DEFAULT_BOOKING_CUTOFF_DAYS),
                        capacity=capacity,
                    )

        self.stdout.write(
            self.style.SUCCESS(
                f"Seeded {len(DESTINATIONS)} destinations, {len(CATEGORIES)} categories "
                f"and {len(ADVENTURES)} adventures."
            )
        )
