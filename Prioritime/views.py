import uuid
from datetime import datetime, timedelta
from functools import wraps

from django.conf import settings
from django.contrib.auth.hashers import make_password, check_password
from django.core.mail import send_mail
from django.http import HttpResponse
from django.http import JsonResponse
from django.template.loader import render_to_string
from rest_framework.decorators import api_view

from db_connection import db, client
from .mongoDB import mongoApi, mongo_utils
from .Model_Logic import dict_to_entities_from_requests, user_preferences
from . import utils
from .Scheduling_Algorithm.automatic_scheduling import re_schedule_tasks, schedule_tasks, schedule_tasks_by_id_list

users_collection = db['users']


def index(request):
    return HttpResponse("Hello, world. You're at the k")


# Wrapper function that versify the user
def user_authorization(view_func):
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if 'Authorization' not in request.headers:
            return JsonResponse({'error': 'Authorization header is missing'}, status=401)

        with client.start_session() as session:
            try:
                session.start_transaction()

                jwt_token = request.headers.get('Authorization')
                user_id = utils.verify_jwt_token(jwt_token)
                if not user_id:
                    session.abort_transaction()
                    return JsonResponse({'error': 'error recovering jwt token'}, status=401)

                if not mongoApi.user_exists(user_id=user_id, session=session):
                    session.abort_transaction()
                    return JsonResponse({'error': 'could not find user'}, status=404)

                confirmed = mongoApi.get_user_info(user_id=user_id, fields=['email_confirmed'], session=session)
                if not confirmed:
                    session.abort_transaction()
                    return JsonResponse({'error': 'Problem loading data'}, status=404)

                if not confirmed['email_confirmed']:
                    session.abort_transaction()
                    return JsonResponse({'error': 'Email not confirmed'}, status=401)

                return view_func(request, user_id, *args, **kwargs)

            except Exception as e:
                session.abort_transaction()
                print(str(e))
                return JsonResponse({'error': str(e)}, status=500)

    return wrapper


@api_view(['POST'])
def register(request):
    if request.method == 'POST':
        email = request.data.get('email')
        password = request.data.get('password')
        first_name = request.data.get('firstName')
        last_name = request.data.get('lastName')
        if email and password:
            with client.start_session() as session:
                try:
                    session.start_transaction()
                    if mongoApi.user_exists(email=email, session=session):
                        session.abort_transaction()
                        return JsonResponse({'error': 'User with this email already exists'}, status=409)

                    # Generate confirmation token
                    confirmation_token = str(uuid.uuid4())

                    # hash the password
                    hashed_password = make_password(password)

                    user_data = utils.create_new_user(email, hashed_password, first_name, last_name, confirmation_token)
                    # Create user document
                    # user_data = {
                    #     'firstName': first_name,
                    #     'lastName': last_name,
                    #     'email': email,
                    #     'password': hashed_password,
                    #     'confirmation_token': confirmation_token,
                    #     'email_confirmed': False,
                    #     'calendar': [],
                    #     'task_list': [],
                    #     'recurring_events': [],
                    #     'recurring_tasks': [],
                    #     'user_preferences': {
                    #         'preferences': {},
                    #         'days_off': [],
                    #         'start_time': time(hour=8).isoformat(),
                    #         'end_time': time(hour=20).isoformat(),
                    #     }
                    # }

                    # Insert user document into MongoDB
                    _id = mongoApi.create_user(user_data, session=session)
                    if not _id:
                        session.abort_transaction()
                        return JsonResponse({'error': 'Failed to create user'}, status=500)

                    # Generate JWT token
                    token = utils.generate_jwt_token(str(_id))

                    # Send confirmation email
                    send_confirmation_email(email, confirmation_token)

                    session.commit_transaction()
                    return JsonResponse({'token': token}, status=201)

                except Exception as e:
                    session.abort_transaction()
                    print(str(e))
                    return JsonResponse({'error': str(e)}, status=500)
        else:
            return JsonResponse({'error': 'Email and password are required'}, status=400)

    return JsonResponse({'error': 'Invalid request method'}, status=405)


def send_confirmation_email(email, confirmation_token):
    subject = 'Confirm Your Email'
    message = render_to_string('confirmation_email.html', {
        'confirmation_link': settings.FRONTEND_BASE_URL + '/api/confirm-email/' + confirmation_token
    })
    try:
        send_mail(subject, message='', html_message=message, from_email=settings.EMAIL_HOST_USER,
                  recipient_list=[email])
        return JsonResponse({'message': 'Confirmation email sent successfully.'}, status=200)
    except Exception as e:
        return JsonResponse({'error': f'An error occurred: {str(e)}'}, status=500)


def confirm_email(request, token):
    with client.start_session() as session:
        try:
            session.start_transaction()
            confirmed = mongoApi.does_email_confirmed(token, session)
            if not confirmed:
                return HttpResponse('Invalid confirmation token.', status=400)

            if confirmed['email_confirmed']:
                return HttpResponse('Email already confirmed.', status=200)

            result = mongoApi.confirm_email(token, session)
            if result:
                session.commit_transaction()
                return HttpResponse('Your email has been confirmed successfully.', status=200)
            else:
                session.abort_transaction()
                return HttpResponse('Could not confirm your email.\n''Please try again later.', status=500)

        except Exception as e:
            session.abort_transaction()
            print(str(e))
            return JsonResponse({'error': str(e)}, status=500)


@api_view(['POST'])
def resend_confirmation_email(request):
    if request.method == 'POST':
        email = request.data.get('email')
        if email is None:
            return JsonResponse({'error': 'Email required'}, status=400)

        with client.start_session() as session:
            try:
                session.start_transaction()
                if mongoApi.user_exists(email=email, session=session):
                    user_info = mongoApi.get_user_info(email=email, fields=['confirmation_token', 'email_confirmed'],
                                                       session=session)
                else:
                    return JsonResponse({'error': 'User with this email does not exist.'}, status=404)

                if not user_info:
                    session.abort_transaction()
                    return JsonResponse({'error': 'Problem loading data'}, status=500)

                email_confirmed = user_info['email_confirmed']
                if email_confirmed:
                    session.abort_transaction()
                    return JsonResponse({'error': 'Email already confirmed'}, status=400)

                confirmation_token = user_info['confirmation_token']
                if confirmation_token:
                    send_confirmation_email(email, confirmation_token)
                    session.commit_transaction()
                    return JsonResponse({'message': 'Confirmation email sent successfully.'}, status=200)

            except Exception as e:
                session.abort_transaction()
                print(str(e))
                return JsonResponse({'error': str(e)}, status=500)

    return JsonResponse({'error': 'Invalid request method'}, status=405)


@api_view(['POST'])
def login(request):
    if request.method == 'POST':
        email = request.data.get('email')
        password = request.data.get('password')
        if not email or not password:
            return JsonResponse({'error': 'Email and password are required'}, status=400)

        with client.start_session() as session:
            try:
                session.start_transaction()
                user_info = mongoApi.get_user_info(email=email, fields=['password', 'email_confirmed', '_id'],
                                                   session=session)
                if not user_info:
                    session.abort_transaction()
                    return JsonResponse({'error': 'User does not exist'}, status=404)

                if check_password(password, user_info['password']):
                    if user_info['email_confirmed']:
                        token = utils.generate_jwt_token(str(user_info['_id']))
                        session.commit_transaction()
                        return JsonResponse({'token': token}, status=200)
                    else:
                        session.abort_transaction()
                        return JsonResponse({'error': 'Email not confirmed'}, status=401)
                else:
                    session.abort_transaction()
                    return JsonResponse({'error': 'Invalid email or password'}, status=400)

            except Exception as e:
                session.abort_transaction()
                print(str(e))
                return JsonResponse({'error': str(e)}, status=500)

    return JsonResponse({'error': 'Invalid request method'}, status=405)


@api_view(['GET'])
@user_authorization
def get_user_info(request, user_id):
    if request.method == 'GET':
        with client.start_session() as session:
            try:
                session.start_transaction()
                result = mongoApi.get_user_info(user_id=user_id, fields=['firstName', 'lastName', 'email'],
                                                session=session)
                if result:
                    session.commit_transaction()
                    return JsonResponse(result, status=200)
                else:
                    session.abort_transaction()
                    return JsonResponse({'error': 'Problem fetching user data'}, status=404)

            except Exception as e:
                session.abort_transaction()
                print(str(e))
                return JsonResponse({'error': str(e)}, status=500)

    return JsonResponse({'error': 'Invalid request method'}, status=405)


@api_view(['PUT'])
@user_authorization
def update_user_info(request, user_id):
    if request.method == 'PUT':
        with client.start_session() as session:
            try:
                session.start_transaction()
                updated_data = request.data
                email = updated_data.get('email')
                if not mongoApi.check_email_can_be_changed(user_id=user_id, email=email, session=session):
                    session.abort_transaction()
                    return JsonResponse({'error': 'User with this email already exists'}, status=409)

                result = mongoApi.update_user_info(user_id, updated_data, session=session)
                if result:
                    session.commit_transaction()
                    return JsonResponse({'message': 'User details updated successfully'}, status=200)
                else:
                    session.abort_transaction()
                return JsonResponse({'error': 'Problem updating user'}, status=400)

            except Exception as e:
                session.abort_transaction()
                print(str(e))
                return JsonResponse({'error': str(e)}, status=500)

    return JsonResponse({'error': 'Invalid request method'}, status=405)


@api_view(['DELETE'])
@user_authorization
def delete_user(request, user_id):
    if request.method == 'DELETE':
        with client.start_session() as session:
            try:
                session.start_transaction()
                result = mongoApi.delete_user(user_id, session=session)
                if result:
                    session.commit_transaction()
                    return JsonResponse({'message': 'User deleted successfully'}, status=200)
                else:
                    session.abort_transaction()
                return JsonResponse({'error': 'Problem deleting user'}, status=500)

            except Exception as e:
                session.abort_transaction()
                print(str(e))
                return JsonResponse({'error': str(e)}, status=500)

    return JsonResponse({'error': 'Invalid request method'}, status=405)


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


@api_view(['POST'])
@user_authorization
def add_event(request, user_id):
    if request.method == 'POST':
        with client.start_session() as session:
            try:
                session.start_transaction()
                event = dict_to_entities_from_requests.create_new_event(request.data)
                date = event.start_time

                if event.frequency == "Once" or event.frequency is None:
                    if mongoApi.add_event(user_id, event, date, session=session):
                        session.commit_transaction()
                        return JsonResponse({'success': 'new event added successfully'}, status=201)
                    else:
                        session.abort_transaction()
                        return JsonResponse({'error': 'problem adding new event to database'}, status=500)
                else:
                    event.first_appearance = date
                    event.item_type = 'recurring event'
                    if mongoApi.add_recurring_event(user_id, event, session=session):
                        session.commit_transaction()
                        return JsonResponse({'success': 'new event added successfully'}, status=201)
                    else:
                        session.abort_transaction()
                        return JsonResponse({'error': 'problem adding new event to database'}, status=500)

            except Exception as e:
                session.abort_transaction()
                print(str(e))
                return JsonResponse({'error': str(e)}, status=500)

    return JsonResponse({'error': 'Invalid request method'}, status=405)


@api_view(['POST'])
@user_authorization
def add_task(request, user_id):
    if request.method == 'POST':
        with client.start_session() as session:
            try:
                session.start_transaction()

                task = dict_to_entities_from_requests.create_new_task(user_id, request.data, session=session)
                if not task or task.deadline < datetime.now():
                    session.abort_transaction()
                    return JsonResponse({'error': 'task could not be added, missing data'}, status=400)

                if task.frequency == "Once" or task.frequency is None:
                    result = mongoApi.add_task(user_id, task, session=session)
                else:
                    task.item_type = 'recurring task'
                    result = mongoApi.add_recurring_task(user_id, task, session=session)

                if result:
                    session.commit_transaction()
                    return JsonResponse({'message': 'Task created successfully'}, status=201)
                else:
                    session.abort_transaction()
                    return JsonResponse({'error': 'task could not be added'}, status=500)

            except Exception as e:
                session.abort_transaction()
                print(str(e))
                return JsonResponse({'error': str(e)}, status=500)

    return JsonResponse({'error': 'Invalid request method'}, status=405)


# @api_view(['POST'])
# @user_authorization
# def add_task_and_automate(request, user_id):
#     if request.method == 'POST':
#         with client.start_session() as session:
#             try:
#                 session.start_transaction()
#
#                 task = dict_to_entities.create_new_task(user_id, request.data, session=session)
#                 if not task:
#                     session.abort_transaction()
#                     return JsonResponse({'error': 'task could not be added, missing data'}, status=400)
#
#                 if task.frequency == "Once" or task.frequency is None:
#                     result = mongoApi.add_task(user_id, task, session=session)
#                     if result:
#                         end_time = task.deadline if task.deadline is not None else (
#                                 datetime.today() + timedelta(days=7))
#                         if schedule_single_task(user_id, task, datetime.today(), end_time, session=session):
#                             session.commit_transaction()
#                             return JsonResponse({'message': 'Task created successfully and scheduled!'}, status=201)
#                         else:
#                             session.abort_transaction()
#                             return JsonResponse({'error': 'task could not be scheduled'}, status=400)
#                     else:
#                         session.abort_transaction()
#                         return JsonResponse({'error': 'failed to add new task'}, status=400)
#                 else:
#                     current_date = datetime(year=datetime.now().year, month=datetime.now().month,
#                                             day=datetime.now().day)
#                     deadline = mongo_utils.find_deadline_for_next_recurring_task(task, current_date)
#                     task_instance = task.generate_recurring_instance(deadline)
#                     task.previous_done = deadline
#                     result = mongoApi.add_recurring_task(user_id, task, session=session)
#                     if result:
#                         if schedule_single_task(user_id, task_instance, datetime.today(), deadline, session=session):
#                             session.commit_transaction()
#                             return JsonResponse({'message': 'Task created successfully and scheduled!'}, status=201)
#                         else:
#                             session.abort_transaction()
#                             return JsonResponse({'error': 'task could not be scheduled'}, status=400)
#                     else:
#                         session.abort_transaction()
#                         return JsonResponse({'error': 'failed to add new task'}, status=400)
#
#             except Exception as e:
#                 session.abort_transaction()
#                 return JsonResponse({'error': str(e)}, status=500)
#
#     return JsonResponse({'error': 'wrong request'}, status=400)

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

                if not schedule_tasks(user_id, [task], datetime.today(), end_time, session=session):
                    session.abort_transaction()
                    return JsonResponse({'error': 'could not schedule the added task'}, status=400)

                session.commit_transaction()
                return JsonResponse({'message': 'Task created and scheduled successfully!'}, status=200)
            except Exception as e:
                session.abort_transaction()
                print(str(e))
                return JsonResponse({'error': str(e)}, status=500)

    return JsonResponse({'error': 'Invalid request method'}, status=405)


@api_view(['GET'])
@user_authorization
def get_event(request, user_id, date):
    if request.method == 'GET':
        event_id = request.data.get('_id')
        if not event_id:
            return JsonResponse({'error': 'missing data'}, status=400)

        with client.start_session() as session:
            try:
                session.start_transaction()
                date = datetime.fromisoformat(date)
                event = mongoApi.get_event(user_id, date, event_id, session=session)
                if event:
                    session.commit_transaction()
                    return JsonResponse(event)
                else:
                    session.abort_transaction()
                    return JsonResponse({'error': 'event not found'}, status=404)

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


@api_view(['PUT'])
@user_authorization
def edit_event(request, user_id, event_id, date):
    if request.method == 'PUT':
        data = dict_to_entities_from_requests.organize_data_edit_event(request.data)
        with client.start_session() as session:
            try:
                session.start_transaction()
                old_date = datetime.fromisoformat(date)
                new_date = old_date if data.get('start_time') is None else datetime.fromisoformat(
                    data.get('start_time'))
                end_date = old_date if data.get('end_time') is None else datetime.fromisoformat(data.get('end_time'))
                if new_date > end_date:
                    session.abort_transaction()
                    return JsonResponse({'error': 'Start comes after end'}, status=400)

                if mongo_utils.update_event(user_id, old_date, new_date, event_id, data, session=session):
                    session.commit_transaction()
                    return JsonResponse({'message': 'Event updated successfully'}, status=200)
                else:
                    session.abort_transaction()
                    return JsonResponse({'error': 'Event could not be updated or does not exist'}, status=400)

            except Exception as e:
                session.abort_transaction()
                print(str(e))
                return JsonResponse({'error': str(e)}, status=500)

    return JsonResponse({'error': 'Invalid request method'}, status=405)


@api_view(['DELETE'])
@user_authorization
def delete_event(request, user_id, event_id, date):
    if request.method == 'DELETE':
        item_type = request.GET.get('type') or request.data.get('item_type')
        with client.start_session() as session:
            try:
                session.start_transaction()
                date = datetime.fromisoformat(date)

                if item_type == 'recurring event':
                    result = mongoApi.delete_recurring_event(user_id, event_id, session=session)
                else:
                    result = mongoApi.delete_event(user_id, date, event_id, session=session)

                if result:
                    session.commit_transaction()
                    return JsonResponse({'message': 'Event deleted successfully'}, status=200)
                else:
                    session.abort_transaction()
                    return JsonResponse({'error': 'Event not found'}, status=404)

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
        updated_data = dict_to_entities_from_requests.organize_data_edit_task(request.data)
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
def get_preferences(request, user_id):
    if request.method == 'GET':
        with client.start_session() as session:
            try:
                session.start_transaction()
                preferences = mongoApi.get_user_preferences(user_id, session=session)
                preferences = user_preferences.PreferenceManager(**preferences)
                if preferences:
                    session.commit_transaction()
                    return JsonResponse(preferences.dict_for_json(), status=200)
                else:
                    session.abort_transaction()
                    return JsonResponse({'error': 'Problem loading data'}, status=400)

            except Exception as e:
                session.abort_transaction()
                print(str(e))
                return JsonResponse({'error': str(e)}, status=500)

    return JsonResponse({'error': 'Invalid request method'}, status=405)


@api_view(['POST'])
@user_authorization
def update_preferences(request, user_id):
    if request.method == 'POST':
        data = request.data
        with client.start_session() as session:
            try:
                session.start_transaction()
                preference_manager = dict_to_entities_from_requests.dict_to_preferences(data)
                result = mongoApi.update_preferences(user_id, preference_manager, session=session)
                if result:
                    session.commit_transaction()
                    return JsonResponse({'message': 'Preferences updated successfully'}, status=200)
                else:
                    session.abort_transaction()
                    return JsonResponse({'error': 'Problem updating preference'}, status=400)

            except Exception as e:
                print(str(e))
                session.abort_transaction()
                return JsonResponse({'error': str(e)}, status=500)

    return JsonResponse({'error': 'Invalid request method'}, status=405)


@api_view(['PUT'])
@user_authorization
def set_day_off(request, user_id, date):
    if request.method == 'PUT':
        day_off = request.data.get('day_off')
        with client.start_session() as session:
            try:
                session.start_transaction()
                date = datetime.fromisoformat(date)
                if mongoApi.update_day_off(user_id, date, day_off, session=session):
                    session.commit_transaction()
                    return JsonResponse({'message': 'Successfully updated'}, status=200)
                else:
                    session.abort_transaction()
                    return JsonResponse({'error': 'problem updating day off'}, status=500)

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

                if schedule_tasks_by_id_list(user_id, tasks_id_list, start_date, end_date, session=session):
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


# @api_view(['POST'])
# @user_authorization
# def re_automate(request, user_id, date):
#     if request.method == 'POST':
#         if len(date) == 7:
#             date = datetime.strptime(date, "%Y-%m")
#             full_date = {'year': date.year,
#                          'month': date.month,
#                          'day': None}
#         elif len(date) == 10:
#             date = datetime.fromisoformat(date)
#             full_date = {'year': date.year,
#                          'month': date.month,
#                          'day': date.day}
#         else:
#             return JsonResponse({'error': 'Wrong date'}, status=500)
#
#         with client.start_session() as session:
#             try:
#                 session.start_transaction()
#                 if re_schedule_tasks(user_id, full_date, session=session):
#                     session.commit_transaction()
#                     return JsonResponse({'message': 'Tasks scheduled successfully'}, status=200)
#                 else:
#                     session.abort_transaction()
#                     return JsonResponse({'error': 'Could not schedule tasks!'}, status=500)
#
#             except Exception as e:
#                 session.abort_transaction()
#                 print(str(e))
#                 return JsonResponse({'error': str(e)}, status=500)
#
#     return JsonResponse({'error': 'Invalid request method'}, status=400)


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
