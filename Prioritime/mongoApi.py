from bson import ObjectId
from db_connection import db
from .views import verify_jwt_token
from . import calendar_objects
import calendar
import json

users = db['users']  # users collection


# returns if the user exists or not
def find_user_by_id(user_id):
    user = db.users.find_one({"_id": {'$exists': ObjectId(user_id)}})
    return user


def get_user_info(user_id):
    user_id = ObjectId(user_id)
    user_info = users.find_one({'_id': user_id}, {'email': 1})  # add more fields that yet to be added
    return user_info


def get_calendar(user_id):
    user_id = ObjectId(user_id)
    full_calendar = users.find_one({"_id": user_id}, {'calendar': 1})
    return full_calendar


def get_yearly_calendar(user_id, year):
    user_id = ObjectId(user_id)
    yearly_calendar = users.calendar.find_one(
        {
            "_id": user_id,
            "year": year,
        },
        {
            "calendar.$": 1  # Projection to include only the matched year
        }
    )
    return yearly_calendar


def get_monthly_calendar(user_id, date):
    user_id = ObjectId(user_id)
    year = date.year
    month = date.month
    monthly_calendar = users.find_one(
        {
            "_id": user_id,
            "calendar.year": year,
            "calendar.months.month": month,
        },
        {
            "calendar.months.$": 1  # Projection to include only the matched month
        }
    )
    return monthly_calendar


# function for loading a daily schedule from the database as a dictionary
def get_schedule(user_id, date):
    user_id = ObjectId(user_id)
    year = date['year']
    month = date['month']
    day = date['day']
    schedule = users.find_one(
        {
            "_id": user_id,
            "calendar.year": year,
            "calendar.months.month": month,
            "calendar.months.days.date": day
        },
        {
            "calendar.months.days.$": 1  # Projection to include only the matched day
        }
    )
    return schedule


def add_new_year(user_id, year):
    user = ObjectId(user_id)
    list_of_monthly_calendars = []
    for m in range(1, 13):
        num_of_days = calendar.monthrange(year, m)[1]
        list_of_schedules = []
        for date in range(1, num_of_days + 1):
            list_of_schedules.append(calendar_objects.Schedule(
                date=date,
                day=calendar.weekday(year, m, date),
            ))

        list_of_monthly_calendars.append(calendar_objects.MonthlyCalendar(
            month=m,
            number_of_days=num_of_days,
            starting_day=calendar.monthrange(year, m)[0],
            list_of_schedules=list_of_schedules
        ))
    yearly_calendar = calendar_objects.YearlyCalendar(
        year=year,
        list_of_monthly_calendars=list_of_monthly_calendars
    )
    yearly_calendar_dict = yearly_calendar.__dict__()
    users.update_one(
        {"_id": user},
        {
            "$addToSet": {
                "calendar": yearly_calendar_dict
            }
        }
    )


# function for checking if a certain year is already presented in the database
def year_exists(user_id, year):
    user = ObjectId(user_id)
    # year_count = users.count_documents({"_id": user, "calendar.year": year})
    year_exist = users.find_one({"_id": user, "calendar.year": {'$exists': year}})
    return year_exist


# Function for adding a new event to a users data base
def add_event(user_id, event, year, month, day):
    user = ObjectId(user_id)

    event_dict = event.__dict__

    # if the year doesn't exist adds it
    if not year_exists(user_id, year):
        add_new_year(user_id, year)

    # Add the event to the appropriate path in the user's calendar
    result = users.update_one(
        {
            "_id": user,
            "calendar.year": year,
            "calendar.months.month": month,
            "calendar.months.days.date": day
        },
        {
            "$addToSet": {
                "calendar.$.months.$[m].days.$[d].event_list": event_dict
            }
        },
        array_filters=[
            {"m.month": month},
            {"d.date": day}
        ]
    )
    # If no matching document is found, create the necessary structure and add the event
    if result.modified_count == 0:
        return False

    return True
