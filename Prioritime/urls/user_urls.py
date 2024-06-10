from django.urls import path
from Prioritime import views

urlpatterns = [
    path('api/register', views.register, name='register'),  # POST
    path('api/login', views.login, name='login'),  # POST
    path('api/confirm-email/<str:token>/', views.confirm_email, name='confirm_email'),
    path('api/resend_confirmation_email/', views.resend_confirmation_email, name='resend_confirmation_email'),  # POST
    path('api/get_user_info/', views.get_user_info, name='get_user_info'),  # GET
    path('api/delete_user/', views.delete_user, name='delete_user'),  # DELETE
    path('api/get_preferences/', views.get_preferences, name='get_preferences'),  # GET
    path('api/update_preferences/', views.update_preferences, name='update_preferences'),  # PUT
    path('api/set_day_off/<str:date>', views.set_day_off, name='set_day_off'),  # PUT
]
