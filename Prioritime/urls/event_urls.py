from django.urls import path
#from Prioritime import views
from Prioritime.Views.event_views import *

# urlpatterns = [
#     path('api/add_event/', views.add_event, name='add_event'),  # POST
#     path('api/get_event/<str:date>', views.get_event, name='get_event'),  # GET
#     path('api/delete_event/<str:event_id>/<str:date>', views.delete_event, name='delete_event'),  # DELETE
#     path('api/update_event/<str:event_id>/<str:date>', views.edit_event, name='edit_event'),  # PUT
#     path('api/get_event/', views.get_event, name='get_event'),  # GET
# ]

urlpatterns = [
    path('add_event/', add_event, name='add_event'),  # POST
    path('get_event/<str:date>', get_event, name='get_event'),  # GET
    path('delete_event/<str:event_id>/<str:date>', delete_event, name='delete_event'),  # DELETE
    path('update_event/<str:event_id>/<str:date>', edit_event, name='edit_event'),  # PUT
    path('get_event/', get_event, name='get_event'),  # GET
]
