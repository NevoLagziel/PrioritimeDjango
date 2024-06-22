from datetime import datetime, timedelta

from django.http import JsonResponse
from rest_framework.decorators import api_view

from db_connection import db, client
from ..Scheduling_Algorithm.automatic_scheduling import re_schedule_tasks, schedule_tasks, schedule_tasks_by_id_list
from ..mongoDB import mongo_utils
from .user_veiws import user_authorization

users_collection = db['users']


@api_view(['GET'])
@user_authorization
def get_schedule(request, user_id, date):
    if request.method == 'GET':
        with client.start_session() as session:
            try:
                session.start_transaction()
                date = datetime.fromisoformat(date)
                schedule = mongo_utils.get_schedule(user_id, date, session=session)
                if schedule:
                    session.commit_transaction()
                    return JsonResponse(schedule.__dict__(), status=200)
                else:
                    session.abort_transaction()
                    return JsonResponse({'error': 'Could not find schedule'}, status=404)

            except Exception as e:
                session.abort_transaction()
                print(str(e))
                return JsonResponse({'error': str(e)}, status=500)

    return JsonResponse({'error': 'Invalid request method'}, status=405)


@api_view(['GET'])
@user_authorization
def get_date_range_schedules(request, user_id, start_date, end_date):
    if request.method == 'GET':
        with client.start_session() as session:
            try:
                session.start_transaction()
                start_date = datetime.fromisoformat(start_date)
                end_date = datetime.fromisoformat(end_date)
                schedules = mongo_utils.get_date_range_schedules(user_id, start_date, end_date, session=session)
                if schedules:
                    session.commit_transaction()
                    return JsonResponse(schedules, status=200)
                else:
                    session.abort_transaction()
                    return JsonResponse({'error': 'Could not find schedules'}, status=404)

            except Exception as e:
                session.abort_transaction()
                print(str(e))
                return JsonResponse({'error': str(e)}, status=500)

    return JsonResponse({'error': 'Invalid request method'}, status=405)


@api_view(['GET'])
@user_authorization
def get_monthly_calendar(request, user_id, date):
    if request.method == 'GET':
        with client.start_session() as session:
            try:
                session.start_transaction()
                date = datetime.strptime(date, "%Y-%m")
                monthly_calendar = mongo_utils.get_monthly_calendar(user_id, date, session=session)
                if monthly_calendar:
                    session.commit_transaction()
                    return JsonResponse(monthly_calendar.__dict__())
                else:
                    session.abort_transaction()
                    return JsonResponse({'error': 'monthly calendar not found'}, status=404)

            except Exception as e:
                session.abort_transaction()
                print(str(e))
                return JsonResponse({'error': str(e)}, status=500)

    return JsonResponse({'error': 'Invalid request method'}, status=405)


@api_view(['POST'])
@user_authorization
def add_task_and_automate(request, user_id):
    if request.method == 'POST':
        with client.start_session() as session:
            try:
                session.start_transaction()
                data = request.data
                task, end_time = mongo_utils.add_task_and_automate(user_id, data, session=session)
                if task is None or end_time is None:
                    session.abort_transaction()
                    return JsonResponse({'error': 'task could not be added'}, status=400)

                results = schedule_tasks(user_id, [task], datetime.today(), end_time, session=session)
                if not results or results[0]['start_time'] is None:
                    session.abort_transaction()
                    return JsonResponse({'error': 'could not schedule the added task'}, status=400)

                session.commit_transaction()
                return JsonResponse({'scheduled_tasks': results}, status=200)
            except Exception as e:
                session.abort_transaction()
                print(str(e))
                return JsonResponse({'error': str(e)}, status=500)

    return JsonResponse({'error': 'Invalid request method'}, status=405)


@api_view(['POST'])
@user_authorization
def automatic_scheduling(request, user_id):
    if request.method == 'POST':
        start_date = request.data.get('start_date')
        end_date = request.data.get('end_date')
        tasks_id_list = request.data.get('tasks')
        if not tasks_id_list:
            return JsonResponse({'error': 'Missing parameters'}, status=400)
        with client.start_session() as session:
            try:
                session.start_transaction()
                if not start_date or not end_date:
                    start_date = datetime.today()
                    end_date = start_date + timedelta(days=30)
                else:
                    start_date = datetime.fromisoformat(start_date)
                    end_date = datetime.fromisoformat(end_date)
                    if start_date > end_date:
                        session.abort_transaction()
                        return JsonResponse({'error': 'Start comes after end'}, status=400)

                results = schedule_tasks_by_id_list(user_id, tasks_id_list, start_date, end_date, session=session)
                if results:
                    session.commit_transaction()
                    return JsonResponse({'scheduled_tasks': results}, status=200)
                else:
                    session.abort_transaction()
                    return JsonResponse({'error': 'Could not schedule tasks!'}, status=500)

            except Exception as e:
                session.abort_transaction()
                print(str(e))
                return JsonResponse({'error': str(e)}, status=500)

    return JsonResponse({'error': 'Invalid request method'}, status=405)


@api_view(['POST'])
@user_authorization
def re_automate(request, user_id):
    if request.method == 'POST':
        with client.start_session() as session:
            try:
                session.start_transaction()
                month = request.GET.get('month')
                date = request.GET.get('date')

                if month is None and date is None:
                    session.abort_transaction()
                    return JsonResponse({'error': 'Missing params!'}, status=400)

                if month is not None and date is not None:
                    session.abort_transaction()
                    return JsonResponse({'error': 'Cant reschedule month and date, pick one!'}, status=400)

                if month is not None:
                    month = datetime.strptime(month, "%Y-%m")
                elif date is not None:
                    date = datetime.fromisoformat(date)

                if re_schedule_tasks(user_id, session=session, month=month, date=date):
                    session.commit_transaction()
                    return JsonResponse({'message': 'Tasks scheduled successfully'}, status=200)
                else:
                    session.abort_transaction()
                    return JsonResponse({'error': 'Could not schedule tasks!'}, status=500)

            except Exception as e:
                session.abort_transaction()
                print(str(e))
                return JsonResponse({'error': str(e)}, status=500)

    return JsonResponse({'error': 'Invalid request method'}, status=405)
