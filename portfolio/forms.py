from django import forms

from .models import Comment, Project


class ProjectForm(forms.ModelForm):
    """Форма создания и редактирования проекта."""

    class Meta:
        model = Project
        fields = ("title", "description", "github_url", "demo_url", "image", "tags")
        widgets = {
            "tags": forms.CheckboxSelectMultiple,
        }


class CommentForm(forms.ModelForm):
    """Форма добавления комментария."""

    class Meta:
        model = Comment
        fields = ("text",)
        labels = {"text": "Ваш комментарий"}
        widgets = {"text": forms.Textarea(attrs={"rows": 3})}


class ModerationForm(forms.Form):
    """Форма модератора: комментарий для автора."""

    comment = forms.CharField(
        label="Комментарий для автора",
        widget=forms.Textarea(attrs={"rows": 4}),
        required=False,
    )
