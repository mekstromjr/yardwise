from django.urls import path

from . import views

urlpatterns = [
    path("", views.today, name="today"),
    path("plants/", views.plant_list, name="plant-list"),
    path("plants/add/", views.plant_form, name="plant-add"),
    path("plants/<int:pk>/", views.plant_detail, name="plant-detail"),
    path("plants/<int:pk>/edit/", views.plant_form, name="plant-edit"),
    path("tasks/", views.task_list, name="task-list"),
    path("tasks/add/", views.task_form, name="task-add"),
    path("tasks/<int:pk>/edit/", views.task_form, name="task-edit"),
    path(
        "occurrences/<int:pk>/<str:action>/",
        views.occurrence_action,
        name="occurrence-action",
    ),
]
