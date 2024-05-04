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
import jwt

JWT_SECRET_KEY = 'b907eca04dbcfea48612202e4011372d9900702fbbee9bb337dab1ba4e7d3424'
JWT_ALGORITHM = 'HS256'
JWT_EXPIRATION_DELTA = timedelta(days=1)


def index(request):
    return HttpResponse("Hello, world. You're at the k")


def generate_jwt_token(_id):
    payload = {
        'user_id': _id,
        'exp': timezone.now() + JWT_EXPIRATION_DELTA  # Token expiry time (24 hours from now)
    }
    return jwt.encode(payload, JWT_SECRET_KEY, JWT_ALGORITHM)


def verify_jwt_token(token):
    try:
        payload = jwt.decode(token, JWT_SECRET_KEY, JWT_ALGORITHM)
        return payload['user_id']
    except (jwt.ExpiredSignatureError, jwt.InvalidTokenError):
        return None


@api_view(['POST'])
def register(request):
    if request.method == 'POST':
        email = request.POST.get('email')
        password = request.POST.get('password')
        if email and password:
            users_collection = db['users']

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
                'email_confirmed': False
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
        send_mail(subject, message, settings.EMAIL_HOST_USER, [email])
        return HttpResponse('Confirmation email sent successfully.')
    except BadHeaderError:
        return HttpResponse('Invalid header found.')
    except Exception as e:
        return HttpResponse(f'An error occurred: {str(e)}')


def confirm_email(request, token):
    # Retrieve the user with the given confirmation token
    users_collection = db['users']
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
        email = request.POST.get('email')
        password = request.POST.get('password')
        if email and password:
            users_collection = db['users']

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
def protected_resource(request):
    if 'Authorization' not in request.headers:
        return Response({'error': 'Authorization header is missing'}, status=401)
    token = request.headers['Authorization'].split()[1]
    user = verify_jwt_token(token)
    if user:
        # This is a protected resource, you can return data specific to the authenticated user
        return Response({'message': f'Hello, {user.email}! This is a protected resource.'})
    else:
        return Response({'error': 'Invalid or expired token'}, status=401)
