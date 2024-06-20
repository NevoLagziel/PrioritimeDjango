import jwt
from config import JWT_SECRET_KEY
from datetime import timedelta, time, datetime
from django.utils import timezone

JWT_ALGORITHM = 'HS256'
JWT_EXPIRATION_DELTA = timedelta(hours=100000)


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


def create_new_user(email, hashed_password, first_name, last_name, confirmation_token):
    user_data = {
        'firstName': first_name,
        'lastName': last_name,
        'email': email,
        'password': hashed_password,
        'confirmation_token': confirmation_token,
        'email_confirmed': False,
        'calendar': [],
        'task_list': [],
        'recurring_events': [],
        'recurring_tasks': [],
        'user_preferences': {
            'preferences': {},
            'days_off': [],
            'start_time': time(hour=8).isoformat(),
            'end_time': time(hour=20).isoformat(),
        }
    }
    return user_data


def is_iso_date(date_string):
    try:
        datetime.fromisoformat(date_string)
        return True
    except ValueError:
        return False
