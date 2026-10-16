
from django.urls import path

from .views import JobApplicationCreateView

urlpatterns = [
    path(
        "applications/",
        JobApplicationCreateView.as_view(),
        name="application-create",
    ),
    path(
        "applications/<int:pk>/",
        JobApplicationCreateView.as_view(),
        name="application-detail",
    ),
]
