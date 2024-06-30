from django.urls import path
from Prioritime.Views.task_views import *

urlpatterns = [
    path('add_task', add_task, name='add_task'),  # POST
    path('update_task/<str:task_id>', edit_task, name='edit_task'),  # PUT
    path('delete_task/<str:task_id>', delete_task, name='delete_task'),  # DELETE
    path('get_task_list/', get_task_list, name='get_task_list'),  # GET
    path('get_recurring_tasks', get_recurring_tasks, name='get_recurring_tasks'),  # GET
]

