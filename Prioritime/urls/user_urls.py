from django.urls import path
from Prioritime.Views.user_veiws import *

urlpatterns = [
    path('register', register, name='register'),  # POST
    path('login', login, name='login'),  # POST
    path('confirm-email/<str:token>/', confirm_email, name='confirm_email'),
    path('resend_confirmation_email/', resend_confirmation_email, name='resend_confirmation_email'),  # POST
    path('change_password', change_password, name='change_password'),  # PUT
    path('get_user_info', get_user_info, name='get_user_info'),  # GET
    path('update_user_info', update_user_info, name='update_user_info'),  # PUT
    path('delete_user/', delete_user, name='delete_user'),  # DELETE
    path('get_preferences/', get_preferences, name='get_preferences'),  # GET
    path('update_preferences', update_preferences, name='update_preferences'),  # PUT
    path('set_day_off/<str:date>', set_day_off, name='set_day_off'),  # PUT
]
