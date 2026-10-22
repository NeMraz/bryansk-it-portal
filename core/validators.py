from django.core.exceptions import ValidationError


MAX_IMAGE_SIZE = 5 * 1024 * 1024


def validate_image_size(file):
    """Ограничивает размер загружаемого изображения пятью мегабайтами.

    Само по себе поле ImageField уже проверяет, что файл — настоящая
    картинка (через Pillow), поэтому здесь остаётся только лимит размера.
    """
    if file.size > MAX_IMAGE_SIZE:
        raise ValidationError("Файл слишком большой. Максимум: 5 МБ.")