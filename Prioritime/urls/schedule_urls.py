from django.urls import path
from Prioritime import views

urlpatterns = [
    path('api/get_schedule/<str:date>', views.get_schedule, name='get_schedule'),  # GET
    path('api/get_monthly_schedule/<str:date>', views.get_monthly_calendar, name='get_monthly_calendar'),  # GET
    path('api/get_date_range_schedules/<str:start_date>/<str:end_date>', views.get_date_range_schedules, name='get_date_range_schedules'),  # GET
    path('api/automatic_scheduling', views.automatic_scheduling, name='automatic_scheduling'),  # POST
    path('api/re_automate/<str:date>', views.re_automate, name='re_automate'),  # POST
    path('api/save_and_automate/', views.add_task_and_automate, name='save_and_automate'),  # POST
]
