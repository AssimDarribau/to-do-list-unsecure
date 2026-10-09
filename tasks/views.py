import json
import logging
import os
import secrets

from django.http import HttpResponse, HttpResponseForbidden
from django.middleware.csrf import get_token
from django.shortcuts import get_object_or_404, redirect, render
from django.utils.html import format_html, format_html_join
from django.utils.http import url_has_allowed_host_and_scheme

from .forms import TaskForm
from .models import Task

logger = logging.getLogger(__name__)

HOME_URL = "/"


def index(request):
    form = TaskForm()

    if request.method == "POST":
        form = TaskForm(request.POST)
        if form.is_valid():
            task = form.save()
            logger.info("Tache ajoutee : %s", task.title)
        return redirect(HOME_URL)

    context = {
        "tasks": Task.objects.all(),
        "form": form,
        "welcome_message": "Bienvenue sur votre TO DO LIST !",
    }
    return render(request, "tasks/list.html", context)


def update_task(request, pk):
    task = get_object_or_404(Task, id=pk)
    form = TaskForm(instance=task)

    if request.method == "POST":
        form = TaskForm(request.POST, instance=task)
        if form.is_valid():
            form.save()
            logger.info("Tache modifiee : %s", task.title)
            return redirect(HOME_URL)

    return render(request, "tasks/update_task.html", {"form": form})


def delete_task(request, pk):
    item = get_object_or_404(Task, id=pk)

    if request.method == "POST":
        item.delete()
        logger.info("Tache supprimee : %s", item.title)
        next_url = request.GET.get("next", HOME_URL)
        if not url_has_allowed_host_and_scheme(
            next_url, allowed_hosts={request.get_host()}, require_https=request.is_secure()
        ):
            next_url = HOME_URL
        return redirect(next_url)

    return render(request, "tasks/delete.html", {"item": item})


def search_tasks(request):
    query = request.GET.get("q", "")
    tasks = Task.objects.filter(title__icontains=query)
    items = format_html_join("", "<li>{}</li>", ((task.title,) for task in tasks))
    return HttpResponse(format_html("<ul>{}</ul>", items))


def import_tasks(request):
    if request.method == "POST":
        try:
            titles = json.loads(request.POST.get("tasks_data", "[]"))
        except json.JSONDecodeError:
            return HttpResponse("Format invalide : liste JSON de titres attendue", status=400)
        if not isinstance(titles, list):
            return HttpResponse("Format invalide : liste JSON de titres attendue", status=400)
        for title in titles:
            form = TaskForm(data={"title": str(title)})
            if form.is_valid():
                form.save()
        return redirect(HOME_URL)

    return HttpResponse(
        format_html(
            "<form method='post'>"
            "<input type='hidden' name='csrfmiddlewaretoken' value='{}'>"
            "<input name='tasks_data' placeholder='[\"tache 1\", \"tache 2\"]'>"
            "<input type='submit'></form>",
            get_token(request),
        )
    )


def admin_panel(request):
    expected = os.environ.get("TODOLIST_ADMIN_PASSWORD", "")
    provided = request.POST.get("pwd", "")
    if expected and provided and secrets.compare_digest(provided, expected):
        return HttpResponse("Bienvenue admin !")
    return HttpResponseForbidden("Acces refuse")
