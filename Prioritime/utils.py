import jwt
from config import JWT_SECRET_KEY
from datetime import timedelta
from django.utils import timezone

JWT_ALGORITHM = 'HS256'
JWT_EXPIRATION_DELTA = timedelta(hours=10)


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

