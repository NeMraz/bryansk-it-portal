from django import forms

from .models import Response, TeamPost


class TeamPostForm(forms.ModelForm):
    """Форма объявления без полей статуса и автора."""

    class Meta:
        model = TeamPost
        fields = ("title", "looking_for", "description")


class ResponseForm(forms.ModelForm):
    """Форма отклика на объявление."""

    class Meta:
        model = Response
        fields = ("message",)
        labels = {"message": "Сообщение автору"}
        widgets = {"message": forms.Textarea(attrs={"rows": 3})}
