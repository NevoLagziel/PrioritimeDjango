from datetime import datetime

from django.http import JsonResponse
from rest_framework.decorators import api_view

from db_connection import db, client
from ..Model_Logic import dict_to_entities
from ..mongoDB import mongoApi, mongo_utils
from .user_veiws import user_authorization

users_collection = db['users']


@api_view(['POST'])
@user_authorization
def add_task(request, user_id):
    if request.method == 'POST':
        with client.start_session() as session:
            try:
                session.start_transaction()
                task = dict_to_entities.create_new_task(user_id, request.data, session=session)
                if not task:
                    session.abort_transaction()
                    return JsonResponse({'error': 'task could not be added, missing data'}, status=400)

                if task.frequency == "Once" or task.frequency is None:
                    result = mongoApi.add_task(user_id, task, session=session)
                else:
                    task.item_type = 'recurring task'
                    result = mongoApi.add_recurring_task(user_id, task, session=session)

                if result:
                    session.commit_transaction()
                    return JsonResponse(task.__dict__(), status=201)
                    # return JsonResponse({'message': 'Task created successfully'}, status=201)
                else:
                    session.abort_transaction()
                    return JsonResponse({'error': 'task could not be added'}, status=500)

            except Exception as e:
                session.abort_transaction()
                print(str(e))
                return JsonResponse({'error': str(e)}, status=500)

    return JsonResponse({'error': 'Invalid request method'}, status=405)


@api_view(['DELETE'])
@user_authorization
def delete_task(request, user_id, task_id):
    if request.method == 'DELETE':
        item_type = request.GET.get('type') or request.data.get('item_type')
        if not task_id:
            return JsonResponse({'error': 'Missing required parameter: _id'}, status=400)

        with client.start_session() as session:
            try:
                session.start_transaction()
                if item_type == 'recurring task':
                    success = mongoApi.delete_recurring_task(user_id, task_id, session=session)
                else:
                    success = mongoApi.delete_task(user_id, task_id, session=session)

                if success:
                    session.commit_transaction()
                    return JsonResponse({'message': 'Task deleted successfully'}, status=200)
                else:
                    session.abort_transaction()
                    return JsonResponse({'error': 'Task not found'}, status=404)

            except Exception as e:
                session.abort_transaction()
                print(str(e))
                return JsonResponse({'error': str(e)}, status=500)

    return JsonResponse({'error': 'Invalid request method'}, status=405)


@api_view(['PUT'])
@user_authorization
def edit_task(request, user_id, task_id):
    if request.method == 'PUT':
        updated_data = dict_to_entities.organize_data_edit_task(request.data)
        with client.start_session() as session:
            try:
                session.start_transaction()
                if mongo_utils.update_task(user_id, task_id, updated_data, session=session):
                    session.commit_transaction()
                    return JsonResponse({'message': 'Task updated successfully'}, status=200)
                else:
                    session.abort_transaction()
                    return JsonResponse({'error': 'Task could not be updated or does not exist'}, status=400)

            except Exception as e:
                session.abort_transaction()
                print(str(e))
                return JsonResponse({'error': str(e)}, status=500)

    return JsonResponse({'error': 'Invalid request method'}, status=405)


@api_view(['GET'])
@user_authorization
def get_task_list(request, user_id):
    if request.method == 'GET':
        date = request.GET.get('date')
        with client.start_session() as session:
            try:
                session.start_transaction()
                if date is not None:
                    date = datetime.fromisoformat(date)

                task_list = mongo_utils.get_task_list(user_id, date, session=session)
                if task_list:
                    # Added for Amit
                    task_list['tasks_count'] = len(task_list['task_list'])
                    session.commit_transaction()
                    return JsonResponse(task_list, status=200)
                else:
                    session.abort_transaction()
                    return JsonResponse({'error': 'Problem loading data'}, status=400)

            except Exception as e:
                session.abort_transaction()
                print(str(e))
                return JsonResponse({'error': str(e)}, status=500)

    return JsonResponse({'error': 'Invalid request method'}, status=405)


@api_view(['GET'])
@user_authorization
def get_recurring_tasks(request, user_id):
    if request.method == 'GET':
        with client.start_session() as session:
            try:
                session.start_transaction()
                task_list = mongoApi.get_recurring_tasks(user_id, session=session)

                if task_list is not None:
                    task_list['tasks_count'] = len(task_list['recurring_tasks'])
                    session.commit_transaction()
                    return JsonResponse(task_list, status=200)
                else:
                    session.abort_transaction()
                    return JsonResponse({'error': 'Problem loading data'}, status=400)

            except Exception as e:
                session.abort_transaction()
                print(str(e))
                return JsonResponse({'error': str(e)}, status=500)

    return JsonResponse({'error': 'Invalid request method'}, status=405)
