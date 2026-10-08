from django.conf import settings
from django.db import models
from django.urls import reverse

from core.validators import validate_image_size


class Tag(models.Model):
    """Тег проекта: Python, Arduino, робототехника и т.д."""

    name = models.CharField("Название", max_length=50, unique=True)

    class Meta:
        verbose_name = "Тег"
        verbose_name_plural = "Теги"
        ordering = ["name"]

    def __str__(self):
        return self.name


class Project(models.Model):
    """Проект школьника в портфолио."""

    class Status(models.TextChoices):
        PENDING = "pending", "На модерации"
        APPROVED = "approved", "Опубликован"
        REJECTED = "rejected", "Отклонён"

    title = models.CharField("Название", max_length=200)
    description = models.TextField("Описание")
    github_url = models.URLField("Ссылка на GitHub", blank=True)
    demo_url = models.URLField("Ссылка на демо или видео", blank=True)
    image = models.ImageField(
        "Картинка",
        upload_to="projects/",
        blank=True,
        validators=[validate_image_size],
    )
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="projects",
        verbose_name="Автор",
    )
    tags = models.ManyToManyField(
        Tag,
        blank=True,
        related_name="projects",
        verbose_name="Теги",
    )
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
        verbose_name = "Проект"
        verbose_name_plural = "Проекты"
        ordering = ["-created_at"]

    def __str__(self):
        return self.title

    def get_absolute_url(self):
        return reverse("portfolio:detail", args=[self.pk])


class Comment(models.Model):
    """Комментарий к проекту."""

    project = models.ForeignKey(
        Project,
        on_delete=models.CASCADE,
        related_name="comments",
        verbose_name="Проект",
    )
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="comments",
        verbose_name="Автор",
    )
    text = models.TextField("Текст", max_length=1000)
    created_at = models.DateTimeField("Дата", auto_now_add=True)

    class Meta:
        verbose_name = "Комментарий"
        verbose_name_plural = "Комментарии"
        ordering = ["created_at"]

    def __str__(self):
        return f"{self.author.username}: {self.text[:30]}"


class Vote(models.Model):
    """Голос пользователя за проект."""

    project = models.ForeignKey(
        Project,
        on_delete=models.CASCADE,
        related_name="votes",
        verbose_name="Проект",
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="votes",
        verbose_name="Пользователь",
    )
    created_at = models.DateTimeField("Дата", auto_now_add=True)

    class Meta:
        verbose_name = "Голос"
        verbose_name_plural = "Голоса"
        constraints = [
            models.UniqueConstraint(fields=["project", "user"], name="unique_vote"),
        ]

    def __str__(self):
        return f"{self.user.username} -> {self.project.title}"
