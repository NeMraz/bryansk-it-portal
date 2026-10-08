from django import forms

from .models import Report


class ReportForm(forms.ModelForm):
    """Форма жалобы; сведения о пользователе и материале задаются на сервере."""

    class Meta:
        model = Report
        fields = ("reason", "details")
        labels = {
            "reason": "Причина",
            "details": "Пояснение (по желанию)",
        }
        widgets = {"details": forms.Textarea(attrs={"rows": 3})}
