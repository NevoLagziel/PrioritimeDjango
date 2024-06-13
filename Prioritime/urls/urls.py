from django.urls import path
from Prioritime import views

urlpatterns = [
    path('', views.index),
    path('api/register', views.register, name='register'),  # POST
    path('api/login', views.login, name='login'),  # POST
    path('api/confirm-email/<str:token>/', views.confirm_email, name='confirm_email'),
    path('api/resend_confirmation_email/', views.resend_confirmation_email, name='resend_confirmation_email'),  # POST
    path('api/get_user_info/', views.get_user_info, name='get_user_info'),  # GET
    path('api/delete_user/', views.delete_user, name='delete_user'),  # DELETE
    path('api/add_event/', views.add_event, name='add_event'),  # POST
    path('api/get_event/<str:date>', views.get_event, name='get_event'),  # GET
    path('api/delete_event/<str:event_id>/<str:date>', views.delete_event, name='delete_event'),  # DELETE
    path('api/update_event/<str:date>', views.edit_event, name='edit_event'),  # PUT
    path('api/get_event/', views.get_event, name='get_event'),  # GET
    path('api/add_task/', views.add_task, name='add_task'),  # POST
    path('api/save_and_automate/', views.add_task_and_automate, name='save_and_automate'),  # POST
    path('api/update_task/<str:task_id>', views.edit_task, name='edit_task'),  # PUT
    path('api/delete_task/<str:task_id>', views.delete_task, name='delete_task'),  # DELETE
    path('api/get_task_list/<str:date>', views.get_task_list, name='get_task_list'),  # GET
    path('api/get_task_list/', views.get_task_list, name='get_task_list'),  # GET
    path('api/get_recurring_tasks', views.get_recurring_tasks, name='get_recurring_tasks'),  # GET
    path('api/automatic_scheduling/', views.automatic_scheduling, name='automatic_scheduling'),  # POST
    path('api/re_automate/', views.re_automate, name='re_automate'),  # POST
    path('api/get_schedule/<str:date>', views.get_schedule, name='get_schedule'),  # GET
    path('api/get_monthly_schedule/<str:date>', views.get_monthly_calendar, name='get_monthly_calendar'),  # GET
    path('api/update_preferences/', views.update_preferences, name='update_preferences'),  # PUT
    path('api/get_preferences/', views.get_preferences, name='get_preferences'),  # GET
    path('api/set_day_off/<str:date>', views.set_day_off, name='set_day_off'),  # PUT
]