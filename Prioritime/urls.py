from django.urls import path
from . import views



urlpatterns = [
    path('', views.index),
    path('get_somthing/', views.get_somthing)
]
