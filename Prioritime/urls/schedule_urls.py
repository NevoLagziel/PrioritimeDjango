from django.urls import path
from Prioritime.Views.schedule_views import *

urlpatterns = [
    path('get_schedule/<str:date>', get_schedule, name='get_schedule'),  # GET
    path('get_monthly_schedule/<str:date>', get_monthly_calendar, name='get_monthly_calendar'),  # GET
    path('get_date_range_schedules/<str:start_date>/<str:end_date>', get_date_range_schedules, name='get_date_range_schedules'),  # GET
    path('automatic_scheduling', automatic_scheduling, name='automatic_scheduling'),  # POST
    path('re_automate/', re_automate, name='re_automate'),  # POST
    path('save_and_automate', add_task_and_automate, name='save_and_automate'),  # POST
]
