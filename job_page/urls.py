
from django.urls import path

from .views import (
    JobApplicationListCreateView,
    JobApplicationDetailView,
)

urlpatterns = [
    path(
        "applications/",
        JobApplicationListCreateView.as_view(),
        name="application-list-create",
    ),
    path(
        "applications/<int:pk>/",
        JobApplicationDetailView.as_view(),
        name="application-detail",
    ),
]
