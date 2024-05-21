from functools import wraps
from django.http import HttpResponse
from django.conf import settings
from django.contrib.auth.hashers import make_password, check_password
from django.http import JsonResponse
from rest_framework.decorators import api_view
from db_connection import db
from django.core.mail import send_mail
import uuid
from django.template.loader import render_to_string
from .utils import generate_jwt_token, verify_jwt_token
from . import mongoApi
from . import calendar_objects
from datetime import datetime
from .Model_Logic import dict_to_entities
from db_connection import client

users_collection = db['users']


def index(request):
    return HttpResponse("Hello, world. You're at the k")


# Wrapper function that versify the user
def user_authorization(view_func):
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if 'Authorization' not in request.headers:
            return JsonResponse({'error': 'Authorization header is missing'}, status=401)
        jwt_token = request.headers.get('Authorization')
        user_id = verify_jwt_token(jwt_token)
        if not user_id:
            return JsonResponse({'error': 'error recovering jwt token'}, status=400)

        if not mongoApi.user_exists(user_id=user_id):
            return JsonResponse({'error': 'could not find user'}, status=400)

        confirmed = mongoApi.get_user_info(user_id=user_id, fields=['email_confirmed'])
        if not confirmed:
            return JsonResponse({'error': 'Problem loading data'})

        if not confirmed['email_confirmed']:
            return JsonResponse({'error': 'Email not confirmed'})

        return view_func(request, user_id, *args, **kwargs)

    return wrapper


@api_view(['POST'])
def register(request):
    if request.method == 'POST':
        email = request.data.get('email')
        password = request.data.get('password')
        if email and password:
            if mongoApi.user_exists(email=email):
                return JsonResponse({'message': 'User with this email already exists'}, status=400)

            # Generate confirmation token
            confirmation_token = str(uuid.uuid4())

            # hash the password
            hashed_password = make_password(password)

            # Create user document
            user_data = {
                'email': email,
                'password': hashed_password,
                'confirmation_token': confirmation_token,
                'email_confirmed': False,
                'calendar': [],
                'task_list': [],
            }

            # Insert user document into MongoDB
            _id = mongoApi.create_user(user_data)
            if not _id:
                return JsonResponse({'error': 'Failed to create user'}, status=400)

            # Generate JWT token
            token = generate_jwt_token(str(_id))

            # Send confirmation email
            send_confirmation_email(email, confirmation_token)

            return JsonResponse({'token': token})
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
        return JsonResponse({'message': 'Confirmation email sent successfully.'})
    except Exception as e:
        return JsonResponse({'error': f'An error occurred: {str(e)}'})


def confirm_email(request, token):
    confirmed = mongoApi.does_email_confirmed(token)
    if confirmed:
        if confirmed['email_confirmed']:
            return HttpResponse('Email already confirmed.')

        result = mongoApi.confirm_email(token)
        if result:
            return HttpResponse('Your email has been confirmed successfully.')

        return HttpResponse('Could not confirm your email.\n'
                            'Please try again later.')
    else:
        # Display an error message or redirect the user to an error page
        return HttpResponse('Invalid confirmation token.')


@api_view(['POST'])
def resend_confirmation_email(request):
    if request.method == 'POST':
        email = request.data.get('email')
        if email:
            if mongoApi.user_exists(email=email):
                user_info = mongoApi.get_user_info(email=email, fields=['confirmation_token', 'email_confirmed'])
                if user_info:
                    email_confirmed = user_info['email_confirmed']
                    if email_confirmed:
                        return JsonResponse({'error': 'Email already confirmed'})

                    confirmation_token = user_info['confirmation_token']
                    if confirmation_token:
                        send_confirmation_email(email, confirmation_token)
                        return JsonResponse({'message': 'Confirmation email sent successfully.'})

                return JsonResponse({'error': 'Problem loading data'})

            return JsonResponse({'error': 'User does not exist.'})

        return JsonResponse({'error': 'Email required'})

    return JsonResponse({'error': 'Invalid request method'})


@api_view(['POST'])
def login(request):
    if request.method == 'POST':
        email = request.data.get('email')
        password = request.data.get('password')
        if email and password:
            user_info = mongoApi.get_user_info(email=email, fields=['password', 'email_confirmed', '_id'])
            if user_info:
                if check_password(password, user_info['password']):
                    if user_info['email_confirmed']:
                        token = generate_jwt_token(str(user_info['_id']))
                        return JsonResponse({'token': token})

                    return JsonResponse({'error': 'Email not confirmed'})

                return JsonResponse({'error': 'Invalid email or password'}, status=400)

            return JsonResponse({'error': 'User does not exist'}, status=404)

        return JsonResponse({'error': 'Email and password are required'}, status=402)

    return JsonResponse({'error': 'Invalid request method'}, status=405)


@api_view(['DELETE'])
@user_authorization
def delete_user(request, user_id):
    if request.method == 'DELETE':
        result = mongoApi.delete_user(user_id)
        if result:
            return JsonResponse({'message': 'User deleted successfully'}, status=200)

        return JsonResponse({'error': 'Problem deleting user'}, status=404)

    return JsonResponse({'error': 'Invalid request method'}, status=405)


@api_view(['GET'])
@user_authorization
def get_schedule(request, user_id):  # doesn't work yet
    if request.method == 'GET':
        date = {'year': request.data.get('year'),
                'month': request.data.get('month'),
                'day': request.data.get('day')}
        schedule = mongoApi.get_schedule(user_id, date)
        return JsonResponse(schedule.__dict__())

    return JsonResponse({'error': 'wrong request'}, status=400)


@api_view(['POST'])
@user_authorization
def add_event(request, user_id):  # need to handle case that event is in more than one day
    if request.method == 'POST':
        name = request.data.get('name')  # str
        description = request.data.get('description')  # str
        duration = request.data.get('duration')  # Useless?
        recurring = request.data.get('recurring')  # string
        category = request.data.get('category')  # str
        tags = request.data.get('tags')  # list of strings
        reminders = request.data.get('reminders')  # int represents minutes
        location = request.data.get('location')
        start_time = request.data.get('start_time')  # datetime ISO string
        end_time = request.data.get('end_time')  # datetime ISO string
        sub_event = request.data.get('sub_event')
        # date = datetime.strptime(start_time, '%Y-%m-%d')
        date = {'year': request.data.get('year'),
                'month': request.data.get('month'),
                'day': request.data.get('day')}

        event = calendar_objects.Event(
            name=name,
            description=description,
            duration=int(duration) if duration else (
                    datetime.strptime(end_time, "%H:%M:%S") - datetime.strptime(start_time, "%H:%M:%S")),
            recurring=recurring,
            category=category,
            tags=tags,
            reminders=reminders,
            location=location,
            start_time=start_time,
            end_time=end_time,  # if end_time else (int(start_time) + int(duration)),
            sub_event=sub_event,
        )

        if event.recurring != "Once":
            event.first_appearance = date
            result = mongoApi.add_recurring_event(user_id, event)
        else:
            if not mongoApi.year_exists(user_id, int(date['year'])):
                mongoApi.add_new_year(user_id, int(date['year']))

            # schedule_dict = mongoApi.get_schedule(user_id, date)  # no need if events could be at the same time
            # schedule = dict_to_entities.dict_to_schedule(schedule_dict)  #
            # if schedule.add_event(event):
            #     result = mongoApi.update_schedule(user_id, date, schedule)
            #     if result:
            #         mongoApi.increment_event_count(user_id, int(date['year']))

            result = mongoApi.add_event(user_id, event, date)
            if result:
                mongoApi.add_recurring_event(user_id, int(date['year']))
                return JsonResponse({'success': 'new event added successfully'})
            else:
                return JsonResponse({'error': 'problem adding new event to database'})

    return JsonResponse({'error': 'wrong request'}, status=400)


@api_view(['POST'])
@user_authorization
def add_task(request, user_id):
    if request.method == 'POST':
        name = request.data.get('name')  # string
        description = request.data.get('description')  # string
        duration = request.data.get('duration')  # number of minutes
        recurring = request.data.get('recurring')  # string
        category = request.data.get('category')  # string
        tags = request.data.get('tags')  # list of strings
        reminders = request.data.get('reminders')  # int (represents time in minutes)
        location = request.data.get('location')  # don't know yet (guess it would be X and Y or google maps object)
        priority = request.data.get('priority')  # don't know yet
        deadline = request.data.get('selectedDateTime')  # ISO string
        status = request.data.get('status')  # string

        task = calendar_objects.Task(
            name=name,
            description=description,
            duration=duration,
            recurring=recurring,
            category=category,
            tags=tags,
            reminders=reminders,
            location=location,
            priority=priority,
            deadline=deadline,
            status=status,
        )

        result = mongoApi.add_task(user_id, task)

        if result:
            return JsonResponse({'message': 'Task created successfully'})

        return JsonResponse({'error': 'task could not be added'}, status=400)

    return JsonResponse({'error': 'wrong request'}, status=405)


@api_view(['GET'])
@user_authorization
def get_event(request, user_id):
    if request.method == 'GET':
        event_id = request.data.get('_id')
        date = {'year': request.data.get('year'),
                'month': request.data.get('month'),
                'day': request.data.get('day')}

        event = mongoApi.get_event(user_id, date, event_id)
        if event:
            return JsonResponse(event)

        return JsonResponse({'error': 'event not found'}, status=404)

    return JsonResponse({'error': 'wrong request'}, status=405)


@api_view(['GET'])
@user_authorization
def get_monthly_calendar(request, user_id):
    if request.method == 'GET':
        date = {'year': request.data.get('year'),
                'month': request.data.get('month')}

        monthly_calendar = mongoApi.get_monthly_calendar(user_id, date)
        if monthly_calendar:
            return JsonResponse(monthly_calendar)

        return JsonResponse({'error': 'monthly calendar empty'}, status=400)

    return JsonResponse({'error': 'wrong request'}, status=400)


@api_view(['DELETE'])
@user_authorization
def delete_event(request, user_id):
    if request.method == 'DELETE':
        event_id = request.data.get('_id')
        date = {'year': request.data.get('year'),
                'month': request.data.get('month'),
                'day': request.data.get('day')}

        if not event_id or not date:
            return JsonResponse({'error': 'Missing required parameters'}, status=400)

        success = mongoApi.delete_event(user_id, date, event_id)
        if success:
            mongoApi.decrement_event_count(user_id, int(date['year']))
            event_count_empty = mongoApi.check_no_events_in_year(user_id, int(date['year']))
            if event_count_empty:
                mongoApi.delete_year(user_id, int(date['year']))

            return JsonResponse({'message': 'Event deleted successfully'})
        else:
            return JsonResponse({'error': 'Event not found'}, status=404)

    return JsonResponse({'error': 'Invalid request method'}, status=405)


@api_view(['DELETE'])
@user_authorization
def delete_task(request, user_id):
    if request.method == 'DELETE':
        task_id = request.data.get('_id')

        if not task_id:
            return JsonResponse({'error': 'Missing required parameter: _id'}, status=400)

        success = mongoApi.delete_task(user_id, task_id)
        if success:
            return JsonResponse({'message': 'Task deleted successfully'})
        else:
            return JsonResponse({'error': 'Task not found'}, status=404)

    return JsonResponse({'error': 'Invalid request method'}, status=405)


@api_view(['GET'])
@user_authorization
def get_task_list(request, user_id):
    if request.method == 'GET':
        task_list = mongoApi.get_task_list(user_id)
        if task_list:
            return JsonResponse(task_list)

        return JsonResponse({'error': 'Problem loading data'}, status=400)

    return JsonResponse({'error': 'Invalid request method'}, status=405)
