import datetime as dt

import pytest
from django.urls import reverse
from django.utils import timezone

pytestmark = pytest.mark.django_db

EVENTS = reverse("events:event-list")
CATEGORIES = reverse("categories:category-list")


def event_url(adventure):
    return reverse("events:event-detail", args=[adventure.slug])


def slugs(response):
    assert response.status_code == 200, response.data
    return [row["slug"] for row in response.data["results"]]


class TestListingVisibility:
    def test_guest_sees_published_event_cards(self, api, make_departure, make_adventure):
        adventure = make_adventure(title="Poon Hill Trek", slug="poon-hill", base_price="30000")
        make_departure(adventure=adventure, days_ahead=20, capacity=10, seats_reserved=4)

        response = api.get(EVENTS)

        assert slugs(response) == ["poon-hill"]
        card = response.data["results"][0]
        assert card["title"] == "Poon Hill Trek"
        assert card["difficulty"] == "moderate"
        assert card["duration_days"] == 5
        assert card["starting_price"] == "30000.00"
        assert card["currency"] == "NPR"
        assert card["destination"]["slug"] == adventure.destination.slug
        assert card["next_departure"]["seats_available"] == 6
        assert card["has_availability"] is True

    def test_card_omits_detail_only_fields(self, api, make_adventure):
        make_adventure()
        card = api.get(EVENTS).data["results"][0]
        for field in ("description", "itinerary", "departures", "cancellation_policy"):
            assert field not in card

    @pytest.mark.parametrize("status", ["draft", "archived"])
    def test_unpublished_events_are_hidden(self, api, make_adventure, status):
        make_adventure(status=status)
        assert slugs(api.get(EVENTS)) == []

    def test_events_of_unpublished_destination_are_hidden(
        self, api, make_adventure, make_destination
    ):
        make_adventure(destination=make_destination(status="draft"))
        assert slugs(api.get(EVENTS)) == []

    def test_event_without_departures_is_listed_as_unavailable(self, api, make_adventure):
        make_adventure(slug="no-dates")
        card = api.get(EVENTS).data["results"][0]
        assert card["next_departure"] is None
        assert card["has_availability"] is False
        assert card["starting_price"] == "25000.00"

    def test_non_bookable_departures_are_ignored(self, api, make_adventure, make_departure):
        adventure = make_adventure()
        make_departure(adventure=adventure, status="cancelled")
        make_departure(adventure=adventure, capacity=5, seats_reserved=5)  # full
        make_departure(  # cutoff passed
            adventure=adventure, booking_cutoff=timezone.now() - dt.timedelta(hours=1)
        )

        card = api.get(EVENTS).data["results"][0]
        assert card["next_departure"] is None
        assert card["has_availability"] is False

    def test_starting_price_uses_cheapest_bookable_departure(
        self, api, make_adventure, make_departure
    ):
        adventure = make_adventure(base_price="50000")
        make_departure(adventure=adventure, days_ahead=40, price_override="42000")
        make_departure(adventure=adventure, days_ahead=20)  # base price
        make_departure(adventure=adventure, price_override="1000", status="cancelled")

        card = api.get(EVENTS).data["results"][0]
        assert card["starting_price"] == "42000.00"
        expected_next = timezone.localdate() + dt.timedelta(days=20)
        assert card["next_departure"]["start_date"] == expected_next.isoformat()

    def test_pagination(self, api, make_adventure):
        for _ in range(15):
            make_adventure()

        first = api.get(EVENTS)
        assert first.data["count"] == 15
        assert len(first.data["results"]) == 12
        assert len(api.get(EVENTS, {"page": 2}).data["results"]) == 3

    def test_listing_query_count_does_not_grow_with_results(
        self, api, make_departure, django_assert_max_num_queries
    ):
        for _ in range(8):
            make_departure()
        with django_assert_max_num_queries(6):
            api.get(EVENTS)


class TestFilters:
    def test_difficulty_accepts_multiple_values(self, api, make_adventure):
        make_adventure(slug="easy", difficulty="easy")
        make_adventure(slug="hard", difficulty="difficult")
        make_adventure(slug="extreme", difficulty="extreme")

        assert slugs(api.get(EVENTS, {"difficulty": "easy"})) == ["easy"]
        assert set(slugs(api.get(EVENTS, {"difficulty": "easy,extreme"}))) == {"easy", "extreme"}

    def test_invalid_difficulty_is_rejected(self, api):
        assert api.get(EVENTS, {"difficulty": "impossible"}).status_code == 400

    def test_activity_type(self, api, make_adventure):
        make_adventure(slug="hike", activity_type="hiking")
        make_adventure(slug="trek", activity_type="trekking")
        assert slugs(api.get(EVENTS, {"activity_type": "hiking"})) == ["hike"]

    def test_destination_region_and_category(
        self, api, make_adventure, make_destination, make_category
    ):
        everest = make_destination(slug="everest", region="Koshi")
        teahouse = make_category(slug="teahouse")
        make_adventure(slug="ebc", destination=everest, category=teahouse)
        make_adventure(slug="other")

        assert slugs(api.get(EVENTS, {"destination": "everest"})) == ["ebc"]
        assert slugs(api.get(EVENTS, {"region": "koshi"})) == ["ebc"]
        assert slugs(api.get(EVENTS, {"category": "teahouse"})) == ["ebc"]

    def test_duration_range(self, api, make_adventure):
        make_adventure(slug="short", duration_days=2)
        make_adventure(slug="medium", duration_days=7)
        make_adventure(slug="long", duration_days=14)

        assert slugs(api.get(EVENTS, {"duration_min": 5, "duration_max": 10})) == ["medium"]

    def test_price_range_uses_starting_price(self, api, make_adventure, make_departure):
        make_adventure(slug="cheap", base_price="10000")
        pricey = make_adventure(slug="discounted", base_price="90000")
        make_departure(adventure=pricey, price_override="20000")
        make_adventure(slug="expensive", base_price="80000")

        result = slugs(api.get(EVENTS, {"price_min": 5000, "price_max": 25000}))
        assert set(result) == {"cheap", "discounted"}

    def test_departure_date_range(self, api, make_adventure, make_departure):
        soon = make_adventure(slug="soon")
        later = make_adventure(slug="later")
        make_departure(adventure=soon, days_ahead=10)
        make_departure(adventure=later, days_ahead=90)
        today = timezone.localdate()

        params = {
            "departure_from": (today + dt.timedelta(days=5)).isoformat(),
            "departure_to": (today + dt.timedelta(days=30)).isoformat(),
        }
        assert slugs(api.get(EVENTS, params)) == ["soon"]

    def test_available_only(self, api, make_adventure, make_departure):
        make_departure(adventure=make_adventure(slug="open"))
        make_departure(adventure=make_adventure(slug="full"), capacity=2, seats_reserved=2)
        make_adventure(slug="no-dates")

        assert slugs(api.get(EVENTS, {"available": "true"})) == ["open"]

    def test_featured(self, api, make_adventure):
        make_adventure(slug="star", is_featured=True)
        make_adventure(slug="plain")
        assert slugs(api.get(EVENTS, {"featured": "true"})) == ["star"]

    def test_search_matches_title_and_destination(self, api, make_adventure, make_destination):
        make_adventure(slug="abc", title="Annapurna Base Camp")
        make_adventure(slug="gokyo", destination=make_destination(name="Everest Region"))
        make_adventure(slug="other", title="Something else")

        assert slugs(api.get(EVENTS, {"search": "annapurna"})) == ["abc"]
        assert slugs(api.get(EVENTS, {"search": "everest"})) == ["gokyo"]


class TestOrdering:
    def test_by_price(self, api, make_adventure):
        make_adventure(slug="b", base_price="20000")
        make_adventure(slug="a", base_price="10000")
        make_adventure(slug="c", base_price="30000")

        assert slugs(api.get(EVENTS, {"ordering": "price"})) == ["a", "b", "c"]
        assert slugs(api.get(EVENTS, {"ordering": "-price"})) == ["c", "b", "a"]

    def test_by_next_departure_date_puts_undated_last(self, api, make_adventure, make_departure):
        make_adventure(slug="undated")
        make_departure(adventure=make_adventure(slug="later"), days_ahead=60)
        make_departure(adventure=make_adventure(slug="sooner"), days_ahead=15)

        assert slugs(api.get(EVENTS, {"ordering": "date"})) == ["sooner", "later", "undated"]

    def test_by_popularity(self, api, make_adventure):
        make_adventure(slug="quiet", popularity=1)
        make_adventure(slug="busy", popularity=50)
        assert slugs(api.get(EVENTS, {"ordering": "-popularity"})) == ["busy", "quiet"]

    def test_unknown_ordering_is_rejected(self, api):
        assert api.get(EVENTS, {"ordering": "password"}).status_code == 400


class TestEventDetail:
    def test_guest_cannot_read_detail(self, api, make_adventure):
        response = api.get(event_url(make_adventure()))
        assert response.status_code == 401
        assert response.data["error"]["code"] == "not_authenticated"

    def test_authenticated_user_gets_full_detail(
        self, auth_client, user, make_adventure, make_departure
    ):
        from apps.adventures.models import ItineraryDay

        adventure = make_adventure(
            slug="abc",
            inclusions=["Guide", "Permits"],
            exclusions=["Flights"],
            cancellation_policy="Free cancellation up to 14 days before departure.",
            max_elevation_m=4130,
        )
        ItineraryDay.objects.create(adventure=adventure, day_number=2, title="Climb")
        ItineraryDay.objects.create(adventure=adventure, day_number=1, title="Arrive")
        make_departure(adventure=adventure, days_ahead=25, capacity=8, price_override="27000")
        make_departure(adventure=adventure, status="cancelled")
        make_adventure(slug="sibling", destination=adventure.destination)
        make_adventure(slug="draft-sibling", destination=adventure.destination, status="draft")

        response = auth_client(user).get(event_url(adventure))

        assert response.status_code == 200
        data = response.data
        assert data["inclusions"] == ["Guide", "Permits"]
        assert data["max_elevation_m"] == 4130
        assert [day["title"] for day in data["itinerary"]] == ["Arrive", "Climb"]
        assert len(data["departures"]) == 1
        departure = data["departures"][0]
        assert departure["price"] == "27000.00"
        assert departure["seats_available"] == 8
        assert departure["min_participants"] == 1
        assert departure["is_bookable"] is True
        assert [item["slug"] for item in data["related"]] == ["sibling"]

    @pytest.mark.parametrize("status", ["draft", "archived"])
    def test_unpublished_detail_is_404_even_for_admins(
        self, auth_client, admin_user, make_adventure, status
    ):
        response = auth_client(admin_user).get(event_url(make_adventure(status=status)))
        assert response.status_code == 404

    def test_unknown_slug_is_404(self, auth_client, user):
        response = auth_client(user).get(reverse("events:event-detail", args=["nope"]))
        assert response.status_code == 404


class TestCategories:
    def test_lists_only_active_categories_in_order(self, api, make_category):
        make_category(slug="second", display_order=2)
        make_category(slug="first", display_order=1)
        make_category(slug="hidden", is_active=False)

        response = api.get(CATEGORIES)
        assert response.status_code == 200
        assert [row["slug"] for row in response.data] == ["first", "second"]
