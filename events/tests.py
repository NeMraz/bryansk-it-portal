from datetime import timedelta

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from core.factories import make_event, make_user

from .models import Event


class EventPagesTests(TestCase):
    def setUp(self):
        self.staff_user = get_user_model().objects.create_user(
            username="event_moderator",
            password="Valid-test-pass-123",
            is_staff=True,
        )

    def create_event(self, title, starts_at, **kwargs):
        return Event.objects.create(
            title=title,
            event_type=kwargs.pop("event_type", Event.Type.WORKSHOP),
            starts_at=starts_at,
            place="Брянск",
            description="Описание события",
            **kwargs,
        )

    def test_empty_list_and_future_events_are_public(self):
        response = self.client.get(reverse("events:list"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Ближайших событий пока нет")

        event = self.create_event(
            "Будущий мастер-класс",
            timezone.now() + timedelta(days=10),
            registration_url="https://example.com/register",
        )
        response = self.client.get(reverse("events:list"))
        self.assertContains(response, event.title)
        self.assertContains(response, event.get_absolute_url())

    def test_list_filters_by_type_and_month_and_ignores_invalid_values(self):
        now = timezone.now()
        competition = self.create_event(
            "Будущее соревнование",
            now + timedelta(days=10),
            event_type=Event.Type.COMPETITION,
        )
        self.create_event(
            "Будущий мастер-класс",
            now + timedelta(days=12),
        )
        matching_month = competition.starts_at.strftime("%Y-%m")

        response = self.client.get(
            reverse("events:list"),
            {"type": Event.Type.COMPETITION, "month": matching_month},
        )
        self.assertEqual(response.context["page_obj"].paginator.count, 1)
        self.assertContains(response, competition.title)
        self.assertNotContains(response, "Будущий мастер-класс")

        response = self.client.get(
            reverse("events:list"),
            {"type": "invalid", "month": "not-a-month"},
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["event_type"], "")
        self.assertEqual(response.context["month"], "")
        self.assertEqual(response.context["page_obj"].paginator.count, 2)

    def test_past_events_are_newest_first_and_show_past_message(self):
        now = timezone.now()
        older = self.create_event("Старое событие", now - timedelta(days=10))
        newer = self.create_event("Недавнее событие", now - timedelta(days=2))

        response = self.client.get(reverse("events:list"), {"past": "1"})

        self.assertEqual(response.status_code, 200)
        self.assertEqual(list(response.context["page_obj"]), [newer, older])
        self.assertContains(response, "Прошедшие")
        self.assertContains(
            self.client.get(newer.get_absolute_url()),
            "Это событие уже прошло",
        )

    def test_unpublished_event_is_hidden_from_public_but_visible_to_staff(self):
        hidden_event = self.create_event(
            "Скрытое событие",
            timezone.now() + timedelta(days=5),
            is_published=False,
        )

        self.assertNotContains(self.client.get(reverse("events:list")), hidden_event.title)
        self.assertEqual(
            self.client.get(hidden_event.get_absolute_url()).status_code,
            404,
        )

        self.client.force_login(self.staff_user)
        response = self.client.get(hidden_event.get_absolute_url())
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Событие скрыто с сайта")
        self.assertContains(response, "Изменить в админке")


class EventRegressionTests(TestCase):
    def test_event_list_and_detail_are_public_and_unpublished_events_are_hidden(self):
        future_event = make_event(title="Открытое событие")
        hidden_event = make_event(
            days=2,
            title="Скрытое событие",
            is_published=False,
        )

        self.assertContains(self.client.get(reverse("events:list")), future_event.title)
        self.assertNotContains(
            self.client.get(reverse("events:list")),
            hidden_event.title,
        )
        self.assertEqual(
            self.client.get(hidden_event.get_absolute_url()).status_code,
            404,
        )

    def test_unpublished_event_is_available_to_staff(self):
        moderator = make_user("event_staff", is_staff=True)
        event = make_event(
            title="Только для сотрудников",
            is_published=False,
        )
        self.client.force_login(moderator)

        response = self.client.get(event.get_absolute_url())
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, event.title)
