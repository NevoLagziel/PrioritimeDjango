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
from ..mongoDB import mongoApi, mongo_utils
from ..Model_Logic import dict_to_entities, user_preferences
from .. import utils

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

                    if len(password) < 8:
                        session.abort_transaction()
                        return JsonResponse({'error': 'Password must be at least 8 characters'}, status=400)

                    # Generate confirmation token
                    confirmation_token = str(uuid.uuid4())

                    # hash the password
                    hashed_password = make_password(password)

                    user_data = utils.create_new_user(email, hashed_password, first_name, last_name, confirmation_token)

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


@api_view(['PUT'])
@user_authorization
def change_password(request, user_id):
    if request.method == 'PUT':
        with client.start_session() as session:
            try:
                session.start_transaction()
                new_password = request.data.get("password")
                if not new_password or len(new_password) < 8:
                    session.abort_transaction()
                    return JsonResponse({'error': 'New password is not valid'}, status=400)

                hashed_password = make_password(new_password)
                updated_data = {"password": hashed_password}

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
                updated_data = dict_to_entities.organize_data_edit_user_info(request.data)
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
        print(data)
        with client.start_session() as session:
            try:
                session.start_transaction()
                preference_manager = dict_to_entities.dict_to_preferences(data)
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
