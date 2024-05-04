from django.urls import path
from . import views


urlpatterns = [
    path('', views.index),
    path('register/', views.register, name='register'),
    path('confirm-email/<str:token>/', views.confirm_email, name='confirm_email'),
    path('login/', views.login, name='login'),
]
