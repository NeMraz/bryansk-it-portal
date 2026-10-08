from functools import wraps
from urllib.parse import urlencode

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.core.paginator import Paginator
from django.db.models import Count
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from .forms import CommentForm, ModerationForm, ProjectForm
from .models import Comment, Project, Tag, Vote


def moderator_required(view_func):
    """Пускает только модераторов (is_staff). Остальным — 403."""

    @wraps(view_func)
    @login_required
    def wrapper(request, *args, **kwargs):
        if not request.user.is_staff:
            raise PermissionDenied
        return view_func(request, *args, **kwargs)

    return wrapper


def project_list(request):
    """Список опубликованных проектов с поиском, тегами и сортировкой."""
    q = request.GET.get("q", "").strip()[:100]
    tag_param = request.GET.get("tag", "")
    selected_tag = (
        int(tag_param)
        if tag_param.isdecimal() and len(tag_param) < 10
        else None
    )

    sort = request.GET.get("sort", "new")
    if sort != "popular":
        sort = "new"

    projects = Project.objects.filter(status=Project.Status.APPROVED)
    if selected_tag:
        projects = projects.filter(tags__id=selected_tag)

    if q:
        q_lower = q.lower()
        matched_ids = [
            project.pk
            for project in projects.only("id", "title", "description")
            if q_lower in project.title.lower() or q_lower in project.description.lower()
        ]
        projects = projects.filter(pk__in=matched_ids)

    projects = (
        projects.select_related("author")
        .prefetch_related("tags")
        .annotate(
            comments_count=Count("comments", distinct=True),
            votes_count=Count("votes", distinct=True),
        )
    )

    if sort == "popular":
        projects = projects.order_by("-votes_count", "-created_at")
    else:
        projects = projects.order_by("-created_at")

    paginator = Paginator(projects, 9)
    page_obj = paginator.get_page(request.GET.get("page"))
    tags = Tag.objects.filter(projects__status=Project.Status.APPROVED).distinct()
    return render(
        request,
        "portfolio/project_list.html",
        {
            "page_obj": page_obj,
            "sort": sort,
            "q": q,
            "selected_tag": selected_tag,
            "tags": tags,
            "filter_query": urlencode({"q": q, "tag": selected_tag or ""}),
        },
    )


def project_detail(request, pk):
    """Страница проекта. Неопубликованные видят только автор и модераторы."""
    project = get_object_or_404(Project, pk=pk)
    if project.status != Project.Status.APPROVED:
        can_see = request.user == project.author or request.user.is_staff
        if not can_see:
            raise Http404

    user_voted = (
        request.user.is_authenticated
        and project.votes.filter(user=request.user).exists()
    )
    return render(
        request,
        "portfolio/project_detail.html",
        {
            "project": project,
            "comments": project.comments.select_related("author"),
            "comment_form": CommentForm(),
            "votes_count": project.votes.count(),
            "user_voted": user_voted,
        },
    )


@login_required
@require_POST
def comment_create(request, pk):
    """Добавление комментария к опубликованному проекту."""
    project = get_object_or_404(Project, pk=pk, status=Project.Status.APPROVED)
    form = CommentForm(request.POST)
    if form.is_valid():
        comment = form.save(commit=False)
        comment.project = project
        comment.author = request.user
        comment.save()
    else:
        messages.error(request, "Комментарий пустой или длиннее 1000 символов.")
    return redirect(project.get_absolute_url() + "#comments")


@login_required
@require_POST
def comment_delete(request, pk):
    """Удаление комментария: автор комментария или модератор."""
    comment = get_object_or_404(Comment, pk=pk)
    if comment.author != request.user and not request.user.is_staff:
        raise PermissionDenied
    project = comment.project
    comment.delete()
    return redirect(project.get_absolute_url() + "#comments")


@login_required
@require_POST
def vote_toggle(request, pk):
    """Поставить или снять голос за проект."""
    project = get_object_or_404(Project, pk=pk, status=Project.Status.APPROVED)
    if project.author == request.user:
        messages.error(request, "Нельзя голосовать за свой проект.")
        return redirect(project)

    vote, created = Vote.objects.get_or_create(project=project, user=request.user)
    if not created:
        vote.delete()
    return redirect(project)


@login_required
def my_projects(request):
    """Мои проекты со статусами модерации."""
    projects = Project.objects.filter(author=request.user).order_by("-created_at")
    return render(request, "portfolio/my_projects.html", {"projects": projects})


@login_required
def project_create(request):
    """Добавление проекта. Сразу уходит на модерацию."""
    if request.method == "POST":
        form = ProjectForm(request.POST, request.FILES)
        if form.is_valid():
            project = form.save(commit=False)
            project.author = request.user
            project.save()
            form.save_m2m()
            messages.success(
                request,
                "Проект отправлен на модерацию. После проверки он появится на сайте.",
            )
            return redirect("portfolio:my")
    else:
        form = ProjectForm()
    return render(request, "portfolio/project_form.html", {"form": form, "title": "Новый проект"})


@login_required
def project_edit(request, pk):
    """Редактирование проекта (только автор). После правки — снова на модерацию."""
    project = get_object_or_404(Project, pk=pk)
    if project.author != request.user:
        raise PermissionDenied

    if request.method == "POST":
        form = ProjectForm(request.POST, request.FILES, instance=project)
        if form.is_valid():
            updated_project = form.save(commit=False)
            updated_project.status = Project.Status.PENDING
            updated_project.moderator_comment = ""
            updated_project.moderated_at = None
            updated_project.save()
            form.save_m2m()
            messages.success(
                request,
                "Изменения сохранены. Проект отправлен на повторную модерацию.",
            )
            return redirect("portfolio:my")
    else:
        form = ProjectForm(instance=project)
    return render(request, "portfolio/project_form.html", {"form": form, "title": "Редактирование проекта"})


@login_required
def project_delete(request, pk):
    """Удаление проекта. Только автор, с подтверждением."""
    project = get_object_or_404(Project, pk=pk)
    if project.author != request.user:
        raise PermissionDenied

    if request.method == "POST":
        project.delete()
        return redirect("portfolio:my")
    return render(request, "portfolio/project_confirm_delete.html", {"project": project})


@moderator_required
def moderation_queue(request):
    """Очередь проектов на проверку. Самые старые — первыми."""
    projects = (
        Project.objects.filter(status=Project.Status.PENDING)
        .select_related("author")
        .order_by("created_at")
    )
    return render(request, "portfolio/moderation_queue.html", {"projects": projects})


@moderator_required
def moderate_project(request, pk):
    """Проверка проекта модератором."""
    project = get_object_or_404(Project, pk=pk)

    if request.method == "POST":
        form = ModerationForm(request.POST)
        action = request.POST.get("action")
        if action == "approve":
            project.status = Project.Status.APPROVED
            project.moderator_comment = form.data.get("comment", "")
            project.moderated_at = timezone.now()
            project.save()
            messages.success(request, "Проект опубликован.")
            return redirect("portfolio:moderation")

        if action == "reject":
            comment = form.data.get("comment", "").strip()
            if not comment:
                form.add_error("comment", "Комментарий обязателен для отклонения проекта.")
            else:
                project.status = Project.Status.REJECTED
                project.moderator_comment = comment
                project.moderated_at = timezone.now()
                project.save()
                messages.success(request, "Проект отклонён и отправлен автору.")
                return redirect("portfolio:moderation")
    else:
        form = ModerationForm(initial={"comment": project.moderator_comment})

    return render(request, "portfolio/moderate.html", {"project": project, "form": form})
