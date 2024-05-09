from django.urls import path
from . import views


urlpatterns = [
    path('api/', views.index),
    path('api/register/', views.register, name='register'),
    path('api/confirm-email/<str:token>/', views.confirm_email, name='confirm_email'),
    path('api/login/', views.login, name='login'),
    path('api/schedule/', views.get_schedule, name='schedule'),
    path('api/add_event/', views.add_event, name='add_event'),
]
