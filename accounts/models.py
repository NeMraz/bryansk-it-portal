from django.conf import settings
from django.db import models

from core.validators import validate_image_size


class Profile(models.Model):
    """Профиль школьника. Расширяет встроенного пользователя Django."""

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="profile",
        verbose_name="Пользователь",
    )
    school = models.CharField("Школа или центр", max_length=200, blank=True)
    city = models.CharField("Город", max_length=100, blank=True)
    interests = models.CharField("Интересы", max_length=200, blank=True)
    about = models.TextField("О себе", blank=True)
    avatar = models.ImageField(
        "Аватар",
        upload_to="avatars/",
        blank=True,
        validators=[validate_image_size],
    )

    class Meta:
        verbose_name = "Профиль"
        verbose_name_plural = "Профили"

    def __str__(self):
        return f"Профиль {self.user.username}"
