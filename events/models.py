from django.db import models
from django.urls import reverse
from django.utils import timezone


class Event(models.Model):
    """Мастер-класс или соревнование в афише."""

    class Type(models.TextChoices):
        WORKSHOP = "workshop", "Мастер-класс"
        COMPETITION = "competition", "Соревнование"

    title = models.CharField("Название", max_length=200)
    event_type = models.CharField(
        "Тип",
        max_length=20,
        choices=Type.choices,
        default=Type.WORKSHOP,
    )
    starts_at = models.DateTimeField("Начало")
    place = models.CharField(
        "Место проведения",
        max_length=200,
        help_text="Адрес или слово «онлайн»",
    )
    description = models.TextField("Описание")
    registration_url = models.URLField("Ссылка на регистрацию", blank=True)
    is_published = models.BooleanField(
        "Опубликовано",
        default=True,
        help_text="Уберите галочку, чтобы скрыть событие с сайта",
    )
    created_at = models.DateTimeField("Дата добавления", auto_now_add=True)

    class Meta:
        verbose_name = "Событие"
        verbose_name_plural = "События"
        ordering = ["starts_at"]

    def __str__(self):
        return self.title

    def get_absolute_url(self):
        return reverse("events:detail", args=[self.pk])

    @property
    def is_past(self):
        """Проверяет, прошло ли событие."""
        return self.starts_at < timezone.now()
