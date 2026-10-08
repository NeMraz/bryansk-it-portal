from urllib.parse import urlencode

from django.core.paginator import Paginator
from django.http import Http404
from django.shortcuts import get_object_or_404, render
from django.utils import timezone

from .models import Event


def event_list(request):
    """Афиша предстоящих или прошедших событий с фильтрами."""
    show_past = request.GET.get("past") == "1"
    now = timezone.now()

    events = Event.objects.filter(is_published=True)
    if show_past:
        events = events.filter(starts_at__lt=now)
    else:
        events = events.filter(starts_at__gte=now)

    months = events.datetimes(
        "starts_at",
        "month",
        order="DESC" if show_past else "ASC",
    )

    event_type = request.GET.get("type", "")
    if event_type in Event.Type.values:
        events = events.filter(event_type=event_type)
    else:
        event_type = ""

    month = request.GET.get("month", "")
    if month:
        try:
            year_str, month_str = month.split("-")
            year, month_number = int(year_str), int(month_str)
            if 2000 <= year <= 2100 and 1 <= month_number <= 12:
                events = events.filter(
                    starts_at__year=year,
                    starts_at__month=month_number,
                )
            else:
                month = ""
        except ValueError:
            month = ""

    events = events.order_by("-starts_at" if show_past else "starts_at")
    paginator = Paginator(events, 10)
    page_obj = paginator.get_page(request.GET.get("page"))

    return render(
        request,
        "events/event_list.html",
        {
            "page_obj": page_obj,
            "show_past": show_past,
            "event_type": event_type,
            "event_types": Event.Type.choices,
            "month": month,
            "months": months,
            "filter_query": urlencode(
                {
                    "type": event_type,
                    "month": month,
                    "past": "1" if show_past else "",
                }
            ),
        },
    )


def event_detail(request, pk):
    """Скрытое событие доступно только сотрудникам сайта."""
    event = get_object_or_404(Event, pk=pk)
    if not event.is_published and not request.user.is_staff:
        raise Http404
    return render(request, "events/event_detail.html", {"event": event})
