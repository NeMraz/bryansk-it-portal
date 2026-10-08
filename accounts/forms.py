from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import UserCreationForm

from .models import Profile


User = get_user_model()


class RegisterForm(UserCreationForm):
    """Форма регистрации с явным согласием на обработку данных."""

    agree = forms.BooleanField(
        label="Я согласен(на) на обработку моих персональных данных",
        error_messages={
            "required": "Без согласия регистрация невозможна.",
        },
    )

    class Meta(UserCreationForm.Meta):
        model = User
        fields = ("username",)


class ProfileForm(forms.ModelForm):
    """Форма редактирования профиля школьника."""

    class Meta:
        model = Profile
        fields = ("school", "city", "interests", "about", "avatar")
