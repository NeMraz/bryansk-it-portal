from django.conf import settings
from django.db import models
from django.urls import reverse


class TeamPost(models.Model):
    """Объявление о поиске команды или участников проекта."""

    class Status(models.TextChoices):
        PENDING = "pending", "На модерации"
        APPROVED = "approved", "Опубликовано"
        REJECTED = "rejected", "Отклонено"

    title = models.CharField("Заголовок", max_length=120)
    looking_for = models.CharField(
        "Кого ищем",
        max_length=150,
        help_text="Например: Python-разработчик, дизайнер",
    )
    description = models.TextField("Описание", max_length=2000)
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="team_posts",
        verbose_name="Автор",
    )
    is_open = models.BooleanField("Набор открыт", default=True)
    status = models.CharField(
        "Статус",
        max_length=10,
        choices=Status.choices,
        default=Status.PENDING,
    )
    moderator_comment = models.TextField("Комментарий модератора", blank=True)
    moderated_at = models.DateTimeField("Дата проверки", null=True, blank=True)
    created_at = models.DateTimeField("Дата создания", auto_now_add=True)
    updated_at = models.DateTimeField("Дата изменения", auto_now=True)

    class Meta:
        verbose_name = "Объявление"
        verbose_name_plural = "Объявления"
        ordering = ["-created_at"]

    def __str__(self):
        return self.title

    def get_absolute_url(self):
        return reverse("team_board:detail", args=[self.pk])


class Response(models.Model):
    """Отклик пользователя на объявление."""

    post = models.ForeignKey(
        TeamPost,
        on_delete=models.CASCADE,
        related_name="responses",
        verbose_name="Объявление",
    )
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="team_responses",
        verbose_name="Кто откликнулся",
    )
    message = models.TextField("Сообщение", max_length=500)
    created_at = models.DateTimeField("Дата", auto_now_add=True)

    class Meta:
        verbose_name = "Отклик"
        verbose_name_plural = "Отклики"
        ordering = ["created_at"]
        constraints = [
            models.UniqueConstraint(fields=["post", "author"], name="unique_response"),
        ]

    def __str__(self):
        return f"{self.author.username} -> {self.post.title}"
