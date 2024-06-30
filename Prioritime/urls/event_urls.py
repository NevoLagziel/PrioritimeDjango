from django.urls import path
from Prioritime.Views.event_views import *

urlpatterns = [
    path('add_event/', add_event, name='add_event'),  # POST
    path('get_event/<str:event_id>/<str:date>', get_event, name='get_event'),  # GET
    path('delete_event/<str:event_id>/<str:date>', delete_event, name='delete_event'),  # DELETE
    path('update_event/<str:event_id>/<str:date>', edit_event, name='edit_event'),  # PUT
    path('get_event/', get_event, name='get_event'),  # GET
]
