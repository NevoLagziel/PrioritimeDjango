from django.urls import path
from . import views


urlpatterns = [
    path('api/', views.index),
    path('api/register/', views.register, name='register'),
    path('api/login/', views.login, name='login'),
    path('api/confirm-email/<str:token>/', views.confirm_email, name='confirm_email'),
    path('api/resend_confirmation_email/', views.resend_confirmation_email, name='resend_confirmation_email'),
    path('api/delete_user/', views.delete_user, name='delete_user'),
    path('api/add_event/', views.add_event, name='add_event'),
    path('api/delete_event/', views.delete_event, name='delete_event'),
    path('api/edit_event/', views.edit_event, name='edit_event'),
    path('api/get_event/', views.get_event, name='get_event'),
    path('api/add_task/', views.add_task, name='add_task'),
    path('api/delete_task/', views.delete_task, name='delete_task'),
    path('api/edit_task/', views.edit_task, name='edit_task'),
    path('api/get_task_list/', views.get_task_list, name='get_task_list'),
    path('api/get_schedule/', views.get_schedule, name='get_schedule'),
    path('api/get_monthly_calendar/', views.get_monthly_calendar, name='get_monthly_calendar'),
    path('api/update_preferences/', views.update_preferences, name='update_preferences'),
]
