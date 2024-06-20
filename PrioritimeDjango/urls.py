from django.contrib import admin
from django.urls import path, include


urlpatterns = [
    path('admin/', admin.site.urls),
    path("api/", include("Prioritime.urls.schedule_urls")),
    path("api/", include("Prioritime.urls.event_urls")),
    path("api/", include("Prioritime.urls.user_urls")),
    path("api/", include("Prioritime.urls.task_urls"))
]
