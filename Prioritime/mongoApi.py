from db_connection import db
from .views import verify_jwt_token


def get_schedule(user, date):
    year = db['calendar'].find_one({'year': date.year})
    month = year.find_one({'month': date.month})
    schedule = month.find_one({'date': date.day})
    return schedule
