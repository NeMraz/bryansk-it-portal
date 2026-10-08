from django.conf import settings
from django.db import models


class Report(models.Model):
    """Жалоба на проект, комментарий, объявление или отклик."""

    class Kind(models.TextChoices):
        PROJECT = "project", "Проект"
        COMMENT = "comment", "Комментарий"
        TEAM_POST = "team_post", "Объявление"
        RESPONSE = "response", "Отклик"

    class Reason(models.TextChoices):
        SPAM = "spam", "Спам или реклама"
        ABUSE = "abuse", "Оскорбления"
        PERSONAL = "personal", "Личные данные"
        INAPPROPRIATE = "inappropriate", "Неподходящее содержание"
        OTHER = "other", "Другое"

    class Status(models.TextChoices):
        NEW = "new", "Новая"
        RESOLVED = "resolved", "Рассмотрена"
        DISMISSED = "dismissed", "Нарушений нет"

    reporter = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="reports",
        verbose_name="Кто пожаловался",
    )
    kind = models.CharField("Тип материала", max_length=20, choices=Kind.choices)
    object_id = models.PositiveIntegerField("ID материала")
    reason = models.CharField("Причина", max_length=20, choices=Reason.choices)
    details = models.TextField("Пояснение", max_length=500, blank=True)
    status = models.CharField(
        "Статус",
        max_length=10,
        choices=Status.choices,
        default=Status.NEW,
    )
    created_at = models.DateTimeField("Дата", auto_now_add=True)
    handled_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="handled_reports",
        verbose_name="Кто рассмотрел",
    )
    handled_at = models.DateTimeField("Дата решения", null=True, blank=True)

    class Meta:
        verbose_name = "Жалоба"
        verbose_name_plural = "Жалобы"
        constraints = [
            models.UniqueConstraint(
                fields=["reporter", "kind", "object_id"],
                name="unique_report",
            ),
        ]

    def __str__(self):
        return f"{self.get_kind_display()} #{self.object_id}: {self.get_reason_display()}"
