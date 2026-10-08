from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.shortcuts import get_object_or_404, redirect, render

from .forms import ProfileForm, RegisterForm
from .models import Profile


def register(request):
    """Зарегистрировать пользователя и сразу создать его профиль."""
    if request.method == "POST":
        form = RegisterForm(request.POST)
        if form.is_valid():
            user = form.save()
            Profile.objects.create(user=user)
            login(request, user)
            return redirect("accounts:profile", user_id=user.id)
    else:
        form = RegisterForm()
    return render(request, "accounts/register.html", {"form": form})


def profile_detail(request, user_id):
    """Показать профиль пользователя всем посетителям."""
    owner = get_object_or_404(User, id=user_id)
    profile, _ = Profile.objects.get_or_create(user=owner)
    return render(
        request,
        "accounts/profile.html",
        {"owner": owner, "profile": profile},
    )


@login_required
def profile_edit(request):
    """Позволить вошедшему пользователю редактировать собственный профиль."""
    profile, _ = Profile.objects.get_or_create(user=request.user)
    if request.method == "POST":
        form = ProfileForm(request.POST, request.FILES, instance=profile)
        if form.is_valid():
            form.save()
            return redirect("accounts:profile", user_id=request.user.id)
    else:
        form = ProfileForm(instance=profile)
    return render(request, "accounts/profile_edit.html", {"form": form})
