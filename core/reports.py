from django.http import Http404
from django.shortcuts import get_object_or_404

from portfolio.models import Comment, Project
from team_board.models import Response, TeamPost


MODELS = {
    "project": Project,
    "comment": Comment,
    "team_post": TeamPost,
    "response": Response,
}


def get_target(report):
    """Материал жалобы или None, если он уже удалён."""
    model = MODELS.get(report.kind)
    if model is None:
        return None
    return model.objects.filter(pk=report.object_id).first()


def describe(kind, obj):
    """Возвращает автора, краткий текст и ссылку на материал."""
    if kind == "project":
        return obj.author, obj.title, obj.get_absolute_url()
    if kind == "comment":
        return obj.author, obj.text[:200], obj.project.get_absolute_url() + "#comments"
    if kind == "team_post":
        return obj.author, obj.title, obj.get_absolute_url()
    if kind == "response":
        return obj.author, obj.message[:200], obj.post.get_absolute_url() + "#responses"
    raise Http404


def find_reportable(kind, pk, user):
    """Находит опубликованный материал, на который пользователь вправе пожаловаться."""
    if kind == "project":
        return get_object_or_404(Project, pk=pk, status=Project.Status.APPROVED)
    if kind == "comment":
        return get_object_or_404(
            Comment.objects.select_related("project"),
            pk=pk,
            project__status=Project.Status.APPROVED,
        )
    if kind == "team_post":
        return get_object_or_404(TeamPost, pk=pk, status=TeamPost.Status.APPROVED)
    if kind == "response":
        obj = get_object_or_404(
            Response.objects.select_related("post"),
            pk=pk,
            post__status=TeamPost.Status.APPROVED,
        )
        if obj.post.author != user:
            raise Http404
        return obj
    raise Http404
