"""Помощники для тестов: быстро создают пользователей и материалы."""

from datetime import timedelta

from django.contrib.auth import get_user_model
from django.utils import timezone

from events.models import Event
from portfolio.models import Project
from team_board.models import TeamPost


PASSWORD = "Str0ng-Pass-2026"


def make_user(username="user", **extra):
    """Создаёт пользователя; для модератора передайте is_staff=True."""
    return get_user_model().objects.create_user(
        username=username,
        password=extra.pop("password", PASSWORD),
        **extra,
    )


def make_project(author, approved=True, **extra):
    """Создаёт опубликованный проект или проект на модерации."""
    data = {
        "title": "Робот-манипулятор",
        "description": "Описание проекта",
        "author": author,
        "status": (
            Project.Status.APPROVED if approved else Project.Status.PENDING
        ),
    }
    data.update(extra)
    return Project.objects.create(**data)


def make_post(author, approved=True, **extra):
    """Создаёт объявление с открытым набором."""
    data = {
        "title": "Ищем дизайнера",
        "looking_for": "Дизайнер интерфейсов",
        "description": "Делаем сайт для школы",
        "author": author,
        "status": (
            TeamPost.Status.APPROVED if approved else TeamPost.Status.PENDING
        ),
        "is_open": True,
    }
    data.update(extra)
    return TeamPost.objects.create(**data)


def make_event(days=7, **extra):
    """Создаёт событие через `days` дней; отрицательное число означает прошлое."""
    data = {
        "title": "Мастер-класс по Python",
        "event_type": Event.Type.WORKSHOP,
        "starts_at": timezone.now() + timedelta(days=days),
        "place": "Брянск, центр цифрового образования",
        "description": "Описание события",
    }
    data.update(extra)
    return Event.objects.create(**data)
