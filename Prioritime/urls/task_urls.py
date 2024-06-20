from django.urls import path
#from Prioritime import views
from Prioritime.Views.task_views import *

# urlpatterns = [
#     path('api/add_task', views.add_task, name='add_task'),  # POST
#     path('api/update_task/<str:task_id>', views.edit_task, name='edit_task'),  # PUT
#     path('api/delete_task/<str:task_id>', views.delete_task, name='delete_task'),  # DELETE
#     path('api/get_task_list/', views.get_task_list, name='get_task_list'),  # GET
#     path('api/get_recurring_tasks', views.get_recurring_tasks, name='get_recurring_tasks'),  # GET
# ]

urlpatterns = [
    path('add_task', add_task, name='add_task'),  # POST
    path('update_task/<str:task_id>', edit_task, name='edit_task'),  # PUT
    path('delete_task/<str:task_id>', delete_task, name='delete_task'),  # DELETE
    path('get_task_list/', get_task_list, name='get_task_list'),  # GET
    path('get_recurring_tasks', get_recurring_tasks, name='get_recurring_tasks'),  # GET
]

