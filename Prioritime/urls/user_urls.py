from django.urls import path
# from Prioritime import views
from Prioritime.Views.user_veiws import *

# urlpatterns = [
#     path('api/register', views.register, name='register'),  # POST
#     path('api/login', views.login, name='login'),  # POST
#     path('api/confirm-email/<str:token>/', views.confirm_email, name='confirm_email'),
#     path('api/resend_confirmation_email/', views.resend_confirmation_email, name='resend_confirmation_email'),  # POST
#     path('api/get_user_info', views.get_user_info, name='get_user_info'),  # GET
#     path('api/update_user_info', views.update_user_info, name='update_user_info'),  # PUT
#     path('api/delete_user/', views.delete_user, name='delete_user'),  # DELETE
#     path('api/get_preferences/', views.get_preferences, name='get_preferences'),  # GET
#     path('api/update_preferences', views.update_preferences, name='update_preferences'),  # PUT
#     path('api/set_day_off/<str:date>', views.set_day_off, name='set_day_off'),  # PUT
# ]

urlpatterns = [
    path('register', register, name='register'),  # POST
    path('login', login, name='login'),  # POST
    path('confirm-email/<str:token>/', confirm_email, name='confirm_email'),
    path('resend_confirmation_email/', resend_confirmation_email, name='resend_confirmation_email'),  # POST
    path('get_user_info', get_user_info, name='get_user_info'),  # GET
    path('update_user_info', update_user_info, name='update_user_info'),  # PUT
    path('delete_user/', delete_user, name='delete_user'),  # DELETE
    path('get_preferences/', get_preferences, name='get_preferences'),  # GET
    path('update_preferences', update_preferences, name='update_preferences'),  # PUT
    path('set_day_off/<str:date>', set_day_off, name='set_day_off'),  # PUT
]