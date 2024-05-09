from functools import wraps
from django.shortcuts import render, redirect
from django.http import HttpResponse
from django.utils.http import urlsafe_base64_decode
from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.hashers import make_password, check_password
from django.http import JsonResponse
from django.utils import timezone
from rest_framework.decorators import api_view
from rest_framework.response import Response
from db_connection import db
from datetime import timedelta
from django.core.mail import send_mail, BadHeaderError
import uuid
from django.template.loader import render_to_string
from django.utils.encoding import force_str
from django.contrib import messages
from .utils import generate_jwt_token, verify_jwt_token
from . import mongoApi

users_collection = db['users']


def index(request):
    return HttpResponse("Hello, world. You're at the k")


# Wrapper function that versify the user
def user_authorization(view_func):
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if 'Authorization' not in request.headers:
            return Response({'error': 'Authorization header is missing'}, status=401)
        jwt_token = request.headers.get('Authorization')
        user_id = verify_jwt_token(jwt_token)
        if not user_id:
            return Response({'error': 'error recovering jwt token'}, status=400)

        user = mongoApi.find_user_by_id(user_id)
        if not user:
            return Response({'error': 'could not find user'}, status=400)

        return view_func(request, user_id, *args, **kwargs)

    return wrapper


@api_view(['POST'])
def register(request):
    if request.method == 'POST':
        email = request.data.get('email')
        password = request.data.get('password')
        if email and password:
            if users_collection.find_one({'email': email}):
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
            }

            # Insert user document into MongoDB
            result = users_collection.insert_one(user_data)
            _id = result.inserted_id
            # Generate JWT token
            token = generate_jwt_token(str(_id))

            # Send confirmation email
            send_confirmation_email(email, confirmation_token)

            return JsonResponse({'token': token})
        else:
            return Response({'error': 'Email and password are required'}, status=400)


def send_confirmation_email(email, confirmation_token):
    subject = 'Confirm Your Email'
    message = render_to_string('confirmation_email.html', {
        'confirmation_link': settings.FRONTEND_BASE_URL + '/confirm-email/' + confirmation_token
    })
    try:
        send_mail(subject, message='', html_message=message, from_email=settings.EMAIL_HOST_USER,
                  recipient_list=[email])
        return HttpResponse('Confirmation email sent successfully.')
    except BadHeaderError:
        return HttpResponse('Invalid header found.')
    except Exception as e:
        return HttpResponse(f'An error occurred: {str(e)}')


def confirm_email(request, token):
    # Retrieve the user with the given confirmation token
    user = users_collection.find_one({'confirmation_token': token})

    if user:
        if user['email_confirmed']:
            return HttpResponse('Email already confirmed.')
        # Mark the user's email as confirmed
        # Update the user document in MongoDB to set email_confirmed = True
        users_collection.update_one({'_id': user['_id']}, {'$set': {'email_confirmed': True}})

        # Optionally, display a success message to the user
        return HttpResponse('Your email has been confirmed successfully.')
    else:
        # Display an error message or redirect the user to an error page
        return HttpResponse('Invalid confirmation token.')


@api_view(['POST'])
def login(request):
    if request.method == 'POST':
        email = request.daat.get('email')
        password = request.data.get('password')
        if email and password:
            # Retrieve user document from MongoDB
            user = users_collection.find_one({'email': email})

            if user and check_password(password, user['password']):
                if not user['email_confirmed']:
                    return HttpResponse('Email must be confirmed.')

                # Generate JWT token
                token = generate_jwt_token(str(user['_id']))

                return JsonResponse({'token': token})
            else:
                return Response({'error': 'Invalid email or password'}, status=400)
        else:
            return Response({'error': 'Email and password are required'}, status=400)


@api_view(['GET'])
@user_authorization
def get_schedule(request, user_id):  # doesn't work yet
    if request.method == 'GET':
        date = {'year': request.data.get('year'), 'month': request.data.get('month'), 'day': request.data.get('day')}
        # date = {'year': year, 'month': month, 'day': day}
        schedule = mongoApi.get_schedule(user_id, date)
        return JsonResponse(schedule)

    return Response({'error': 'wrong request'}, status=400)


@api_view(['POST'])
@user_authorization
def add_event(request, user_id):  # need to add an event creation function that checks if its fine to add it
    if request.method == 'POST':
        event = request.data.get('event')  # not getting an event from the front, getting details need to add function to build event
        date = request.data.get('date')
        mongoApi.add_event(user_id, event, date.year, date.month, date.day)
        return Response({'success': 'new event added successfully'})

    return Response({'error': 'wrong request'}, status=400)
