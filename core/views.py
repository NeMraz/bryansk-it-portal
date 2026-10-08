from django.contrib.auth import get_user_model
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Count
from django.http import HttpResponseBadRequest
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from events.models import Event
from portfolio.models import Project
from portfolio.views import moderator_required
from team_board.models import TeamPost

from .forms import ReportForm
from .models import Report
from .reports import describe, find_reportable, get_target


def home(request):
    """Главная страница: свежее из всех разделов сайта."""
    User = get_user_model()

    projects = (
        Project.objects.filter(status=Project.Status.APPROVED)
        .select_related("author")
        .annotate(votes_count=Count("votes"))
        .order_by("-created_at")[:6]
    )

    events = (
        Event.objects.filter(is_published=True, starts_at__gte=timezone.now())
        .order_by("starts_at")[:4]
    )

    open_posts = TeamPost.objects.filter(
        status=TeamPost.Status.APPROVED,
        is_open=True,
    )
    posts = open_posts.select_related("author")[:4]

    stats = {
        "projects": Project.objects.filter(status=Project.Status.APPROVED).count(),
        "users": User.objects.count(),
        "open_posts": open_posts.count(),
    }

    return render(
        request,
        "core/home.html",
        {
            "projects": projects,
            "events": events,
            "posts": posts,
            "stats": stats,
        },
    )


def about(request):
    return render(request, "core/about.html", {"title": "О проекте"})


@login_required
def report_create(request, kind, pk):
    """Создаёт жалобу на опубликованный материал."""
    target = find_reportable(kind, pk, request.user)
    author, preview, url = describe(kind, target)

    if author == request.user:
        messages.error(request, "Нельзя пожаловаться на свой материал.")
        return redirect(url)

    if request.method == "POST":
        form = ReportForm(request.POST)
        if form.is_valid():
            report, created = Report.objects.get_or_create(
                reporter=request.user,
                kind=kind,
                object_id=pk,
                defaults={
                    "reason": form.cleaned_data["reason"],
                    "details": form.cleaned_data["details"],
                },
            )
            if created:
                messages.success(request, "Спасибо! Жалоба отправлена модераторам.")
            else:
                messages.info(
                    request,
                    "Вы уже отправляли жалобу на этот материал. Модераторы её рассмотрят.",
                )
            return redirect(url)
    else:
        form = ReportForm()

    return render(
        request,
        "core/report_form.html",
        {"form": form, "preview": preview, "url": url},
    )


@moderator_required
def report_queue(request):
    """Показывает модераторам очередь новых жалоб."""
    reports = (
        Report.objects.filter(status=Report.Status.NEW)
        .select_related("reporter")
        .order_by("created_at")[:50]
    )
    items = []
    for report in reports:
        target = get_target(report)
        item = {"report": report, "target": target}
        if target is not None:
            author, preview, url = describe(report.kind, target)
            item.update(author=author, preview=preview, url=url)
        items.append(item)
    return render(request, "core/report_queue.html", {"items": items})


@moderator_required
@require_POST
def report_handle(request, pk):
    """Закрывает жалобу или удаляет нарушающий комментарий/отклик."""
    report = get_object_or_404(Report, pk=pk, status=Report.Status.NEW)
    action = request.POST.get("action")
    now = timezone.now()

    if action == "delete" and report.kind in (
        Report.Kind.COMMENT,
        Report.Kind.RESPONSE,
    ):
        target = get_target(report)
        if target is not None:
            target.delete()
        Report.objects.filter(
            kind=report.kind,
            object_id=report.object_id,
            status=Report.Status.NEW,
        ).update(
            status=Report.Status.RESOLVED,
            handled_by=request.user,
            handled_at=now,
        )
        messages.success(request, "Материал удалён, жалобы закрыты.")
    elif action in ("resolve", "dismiss"):
        report.status = (
            Report.Status.RESOLVED
            if action == "resolve"
            else Report.Status.DISMISSED
        )
        report.handled_by = request.user
        report.handled_at = now
        report.save(update_fields=["status", "handled_by", "handled_at"])
        messages.success(request, "Жалоба закрыта.")
    else:
        return HttpResponseBadRequest("Неизвестное действие")

    return redirect("core:reports")
