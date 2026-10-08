from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.core.paginator import Paginator
from django.db.models import Count
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from portfolio.forms import ModerationForm
from portfolio.views import moderator_required

from .forms import ResponseForm, TeamPostForm
from .models import Response, TeamPost


def post_list(request):
    """Опубликованные объявления; закрытые показываются отдельно."""
    show_closed = request.GET.get("closed") == "1"
    posts = TeamPost.objects.filter(
        status=TeamPost.Status.APPROVED,
    ).select_related("author")
    if not show_closed:
        posts = posts.filter(is_open=True)

    paginator = Paginator(posts, 10)
    page_obj = paginator.get_page(request.GET.get("page"))
    return render(
        request,
        "team_board/post_list.html",
        {"page_obj": page_obj, "show_closed": show_closed},
    )


def post_detail(request, pk):
    """Неопубликованное объявление доступно только автору и модераторам."""
    post = get_object_or_404(TeamPost, pk=pk)
    is_owner = request.user == post.author
    is_moderator = request.user.is_staff
    if post.status != TeamPost.Status.APPROVED and not (is_owner or is_moderator):
        raise Http404

    can_see_responses = is_owner or is_moderator
    already_responded = (
        request.user.is_authenticated
        and post.responses.filter(author=request.user).exists()
    )
    return render(
        request,
        "team_board/post_detail.html",
        {
            "post": post,
            "is_owner": is_owner,
            "can_see_responses": can_see_responses,
            "responses": (
                post.responses.select_related("author") if can_see_responses else None
            ),
            "already_responded": already_responded,
            "response_form": ResponseForm(),
        },
    )


@login_required
def my_posts(request):
    """Список объявлений пользователя со статусами и числом откликов."""
    posts = (
        TeamPost.objects.filter(author=request.user)
        .annotate(responses_count=Count("responses"))
    )
    return render(request, "team_board/my_posts.html", {"posts": posts})


@login_required
def post_create(request):
    """Новое объявление сразу отправляется на модерацию."""
    if request.method == "POST":
        form = TeamPostForm(request.POST)
        if form.is_valid():
            post = form.save(commit=False)
            post.author = request.user
            post.save()
            messages.success(
                request,
                "Объявление отправлено на модерацию. После проверки оно появится на доске.",
            )
            return redirect("team_board:my")
    else:
        form = TeamPostForm()
    return render(
        request,
        "team_board/post_form.html",
        {"form": form, "title": "Новое объявление"},
    )


@login_required
def post_edit(request, pk):
    """Автор может отредактировать объявление; изменения требуют новой модерации."""
    post = get_object_or_404(TeamPost, pk=pk)
    if post.author != request.user:
        raise PermissionDenied

    if request.method == "POST":
        form = TeamPostForm(request.POST, instance=post)
        if form.is_valid():
            post = form.save(commit=False)
            post.status = TeamPost.Status.PENDING
            post.moderator_comment = ""
            post.moderated_at = None
            post.save()
            messages.success(
                request,
                "Изменения сохранены. Объявление отправлено на повторную модерацию.",
            )
            return redirect("team_board:my")
    else:
        form = TeamPostForm(instance=post)
    return render(
        request,
        "team_board/post_form.html",
        {"form": form, "title": "Редактирование объявления"},
    )


@login_required
@require_POST
def post_toggle_open(request, pk):
    """Автор закрывает или снова открывает набор без повторной модерации."""
    post = get_object_or_404(TeamPost, pk=pk)
    if post.author != request.user:
        raise PermissionDenied
    post.is_open = not post.is_open
    post.save(update_fields=["is_open", "updated_at"])
    return redirect(post)


@login_required
def post_delete(request, pk):
    """Удаление объявления доступно автору после подтверждения."""
    post = get_object_or_404(TeamPost, pk=pk)
    if post.author != request.user:
        raise PermissionDenied

    if request.method == "POST":
        post.delete()
        return redirect("team_board:my")
    return render(request, "team_board/post_confirm_delete.html", {"post": post})


@login_required
@require_POST
def response_create(request, pk):
    """Создать один отклик на открытое опубликованное объявление."""
    post = get_object_or_404(
        TeamPost,
        pk=pk,
        status=TeamPost.Status.APPROVED,
    )
    if post.author == request.user:
        messages.error(request, "Нельзя откликнуться на своё объявление.")
    elif not post.is_open:
        messages.error(request, "Набор в команду уже закрыт.")
    else:
        form = ResponseForm(request.POST)
        if form.is_valid():
            response, created = Response.objects.get_or_create(
                post=post,
                author=request.user,
                defaults={"message": form.cleaned_data["message"]},
            )
            if created:
                messages.success(
                    request,
                    "Отклик отправлен. Автор увидит его в своём объявлении.",
                )
            else:
                messages.error(request, "Вы уже откликались на это объявление.")
        else:
            messages.error(request, "Напишите сообщение (не длиннее 500 символов).")
    return redirect(post)


@moderator_required
def moderation_queue(request):
    """Очередь объявлений на модерацию, старые объявления первыми."""
    posts = (
        TeamPost.objects.filter(status=TeamPost.Status.PENDING)
        .select_related("author")
        .order_by("created_at")
    )
    return render(request, "team_board/moderation_queue.html", {"posts": posts})


@moderator_required
def moderate_post(request, pk):
    """Опубликовать объявление или отклонить с причиной."""
    post = get_object_or_404(TeamPost, pk=pk)
    form = ModerationForm(request.POST or None)

    if request.method == "POST" and form.is_valid():
        action = request.POST.get("action")
        comment = form.cleaned_data["comment"].strip()

        if action == "approve":
            post.status = TeamPost.Status.APPROVED
        elif action == "reject" and comment:
            post.status = TeamPost.Status.REJECTED
        else:
            form.add_error(
                "comment",
                "Чтобы отклонить объявление, напишите причину.",
            )
            return render(
                request,
                "team_board/moderate.html",
                {"form": form, "post": post},
            )

        post.moderator_comment = comment
        post.moderated_at = timezone.now()
        post.save()
        messages.success(
            request,
            f"Объявление «{post.title}»: {post.get_status_display()}.",
        )
        return redirect("team_board:moderation")

    return render(
        request,
        "team_board/moderate.html",
        {"form": form, "post": post},
    )
