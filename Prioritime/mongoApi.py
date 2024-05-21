from datetime import datetime

from bson import ObjectId
from db_connection import db
from . import calendar_objects
import calendar
from .Model_Logic import dict_to_entities

users = db['users']  # users collection


# returns if the user exists or not
def user_exists(user_id=None, email=None):
    user_exist = 0
    if user_id:
        user_exist = users.count_documents({'_id': ObjectId(user_id)})
    elif email:
        user_exist = users.count_documents({'email': email})
    return user_exist == 1


def create_user(user_data):
    result = users.insert_one(user_data)
    if not result:
        return False

    return result.inserted_id


def delete_user(user_id):
    result = users.delete_one({'_id': ObjectId(user_id)})
    return result.deleted_count == 1


def does_email_confirmed(confirmation_token):
    result = users.find_one(
        {'confirmation_token': confirmation_token},
        {
            'email_confirmed': 1,
            '_id': 0,
        }
    )
    return result


def confirm_email(confirmation_token):
    result = users.update_one(
        {'confirmation_token': confirmation_token},
        {'$set': {'email_confirmed': True}}
    )
    return result.modified_count == 1


def get_user_info(user_id=None, email=None, fields=None):
    user_info = None
    projection = {}
    exclude_id = True
    if fields:
        for field in fields:
            projection[field] = 1
            if field == '_id':
                exclude_id = False

        if exclude_id:
            projection['_id'] = 0

    if user_id:
        user_id = ObjectId(user_id)
        user_info = users.find_one({'_id': user_id}, projection)

    elif email:
        user_info = users.find_one({'email': email}, projection)

    return user_info


def get_event(user_id, date, event_id):
    user_id = ObjectId(user_id)
    year = int(date['year'])
    month = int(date['month'])
    day = int(date['day'])
    event_dict = users.aggregate([
        {"$match": {"_id": user_id}},
        {"$unwind": "$calendar"},
        {"$match": {"calendar.year": year}},
        {"$unwind": "$calendar.months"},
        {"$match": {"calendar.months.month": month}},
        {"$unwind": "$calendar.months.days"},
        {"$match": {"calendar.months.days.date": day}},
        {"$unwind": "$calendar.months.days.event_list"},
        {"$match": {"calendar.months.days.event_list._id": event_id}},
        {"$replaceRoot": {"newRoot": "$calendar.months.days.event_list"}}
    ])
    event_dict = list(event_dict)
    if not event_dict:
        return None

    return event_dict[0]


def delete_event(user_id, date, event_id):
    user_id = ObjectId(user_id)
    year = int(date['year'])
    month = int(date['month'])
    day = int(date['day'])
    result = users.update_one(
        {
            "_id": user_id,
            "calendar.year": year,
            "calendar.months.month": month,
            "calendar.months.days.date": day
        },
        {
            "$pull": {
                "calendar.$[y].months.$[m].days.$[d].event_list": {"_id": event_id}
            }
        },
        array_filters=[
            {"y.year": year},
            {"m.month": month},
            {"d.date": day}
        ]
    )
    if result.modified_count > 0:
        return True

    return False


def get_calendar(user_id):
    user_id = ObjectId(user_id)
    full_calendar = users.find_one({"_id": user_id}, {'calendar': 1})
    return full_calendar


def get_yearly_calendar(user_id, year):
    user_id = ObjectId(user_id)
    yearly_calendar = users.aggregate([
        {"$match": {"_id": user_id}},
        {"$unwind": "$calendar"},
        {"$match": {"calendar.year": year}},
        {"$replaceRoot": {"newRoot": "$calendar"}}
    ])

    yearly_calendar = list(yearly_calendar)
    if not yearly_calendar:
        return None

    return yearly_calendar[0]


def get_monthly_calendar(user_id, date):
    user_id = ObjectId(user_id)
    year = int(date['year'])
    month = int(date['month'])
    monthly_calendar = users.aggregate([
        {"$match": {"_id": user_id}},
        {"$unwind": "$calendar"},
        {"$match": {"calendar.year": year}},
        {"$unwind": "$calendar.months"},
        {"$match": {"calendar.months.month": month}},
        {"$replaceRoot": {"newRoot": "$calendar.months"}}
    ])
    monthly_calendar = list(monthly_calendar)
    if not monthly_calendar:
        return None

    return monthly_calendar[0]


# function for loading a daily schedule from the database as a dictionary
def get_schedule(user_id, date):
    year = int(date['year'])
    month = int(date['month'])
    day = int(date['day'])
    user_id = ObjectId(user_id)

    # Execute the aggregation pipeline
    schedule = users.aggregate([
        {"$match": {"_id": user_id}},
        {"$unwind": "$calendar"},
        {"$match": {"calendar.year": year}},
        {"$unwind": "$calendar.months"},
        {"$match": {"calendar.months.month": month}},
        {"$unwind": "$calendar.months.days"},
        {"$match": {"calendar.months.days.date": day}},
        {"$replaceRoot": {"newRoot": "$calendar.months.days"}}
    ])

    schedule = list(schedule)
    if not schedule:
        return None

    return schedule[0]


def update_schedule(user_id, date, schedule):
    user_id = ObjectId(user_id)
    year = int(date['year'])
    month = int(date['month'])
    day = int(date['day'])
    schedule_dict = schedule.__dict__()
    result = users.update_one(
        {
            "_id": user_id,
            "calendar.year": year,
            "calendar.months.month": month,
            "calendar.months.days.date": day
        },
        {
            '$set': {
                "calendar.$[y].months.$[m].days.$[d]": schedule_dict
            }
        },
        array_filters=[
            {"y.year": year},
            {"m.month": month},
            {"d.date": day}
        ]
    )
    if result.modified_count == 0:
        return False

    return True


# not sure if needed
def add_new_year(user_id, year):
    user = ObjectId(user_id)
    list_of_monthly_calendars = []
    for m in range(1, 13):
        num_of_days = calendar.monthrange(year, m)[1]
        list_of_schedules = []
        for date in range(1, num_of_days + 1):
            list_of_schedules.append(calendar_objects.Schedule(
                date=date,
                day=(calendar.weekday(year, m, date) + 1),
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
    result = users.update_one(
        {"_id": user},
        {
            "$addToSet": {
                "calendar": yearly_calendar_dict
            }
        }
    )
    if result.modified_count == 0:
        return False

    return True


# function for checking if a certain year is already presented in the database
def year_exists(user_id, year):
    user = ObjectId(user_id)
    year_count = users.count_documents({"_id": user, "calendar.year": year})
    return year_count > 0


def delete_year(user_id, year):
    user_id = ObjectId(user_id)
    result = users.update_one(
        {
            "_id": user_id,
            "calendar": {
                "$elemMatch": {"year": year}
            }
        },
        {
            "$pull": {
                "calendar": {"year": year}
            }
        }
    )
    if result.modified_count > 0:
        return True

    return False


# Function for adding a new event to a users database without checking collisions
def add_event(user_id, event, date):
    year = int(date['year'])
    month = int(date['month'])
    day = int(date['day'])
    # if the year doesn't exist adds it
    if not year_exists(user_id, year):
        add_new_year(user_id, year)

    user_id = ObjectId(user_id)
    event_dict = event.__dict__()

    # Add the event to the appropriate path in the user's calendar
    result = users.update_one(
        {
            "_id": user_id,
            "calendar.year": year,
            "calendar.months.month": month,
            "calendar.months.days.date": day
        },
        {
            "$addToSet": {
                "calendar.$[y].months.$[m].days.$[d].event_list": event_dict
            }
        },
        array_filters=[
            {"y.year": year},
            {"m.month": month},
            {"d.date": day}
        ]
    )
    # If no matching document is found, create the necessary structure and add the event
    if result.modified_count == 0:
        return False

    return True


def add_recurring_event(user_id, event):
    user_id = ObjectId(user_id)
    event_dict = event.__dict__()
    result = users.update_one(
        {"_id": user_id},
        {
            "$addToSet": {
                "recurring_events": event_dict
            }
        }
    )
    if result.modified_count == 0:
        return False

    return True


def get_recurring_events(user_id):
    user_id = ObjectId(user_id)
    recurring_events = users.find_one(
        {"_id": user_id},
        {
            "recurring_events": 1,
            "_id": 0,
        }
    )
    return recurring_events


def get_task_list(user_id):  # returns tasks list as dictionary
    user_id = ObjectId(user_id)
    task_list = users.find_one(
        {"_id": user_id},
        {
            "task_list": 1,
            "_id": 0,
        }
    )
    return task_list


def add_task(user_id, task):
    user_id = ObjectId(user_id)
    task_dict = task.__dict__()
    result = users.update_one(
        {
            "_id": user_id,
        },
        {
            "$addToSet": {
                "task_list": task_dict
            }
        }
    )
    if result.modified_count == 0:
        return False

    return True


def delete_task(user_id, task_id):
    user_id = ObjectId(user_id)
    result = users.update_one(
        {"_id": user_id},
        {"$pull": {"task_list": {"_id": task_id}}}
    )
    if result.modified_count > 0:
        return True

    return False


def check_no_events_in_year(user_id, year):
    user_id = ObjectId(user_id)
    event_count_zero = users.count_documents(
        {
            "_id": user_id,
            "calendar.year": year,
            "calendar.event_count": 0
        }
    )
    if event_count_zero > 0:
        return True

    return False


def increment_event_count(user_id, year):
    user_id = ObjectId(user_id)
    result = users.update_one(
        {
            "_id": user_id,
            "calendar.year": year
        },
        {
            "$inc": {
                "calendar.$.event_count": 1
            }
        }
    )
    if result.modified_count > 0:
        return True

    return False


def decrement_event_count(user_id, year):
    user_id = ObjectId(user_id)
    result = users.update_one(
        {
            "_id": user_id,
            "calendar.year": year
        },
        {
            "$inc": {
                "calendar.$.event_count": -1
            }
        }
    )
    if result.modified_count > 0:
        return True

    return False


# Two functions for handling reoccurring events
def get_dally_schedule(user_id, date):
    schedule_dict = get_schedule(user_id, date)
    if schedule_dict:
        schedule = dict_to_entities.dict_to_schedule(schedule_dict)
    else:
        day = int(date['day'])
        month = int(date['month'])
        year = int(date['year'])
        schedule = calendar_objects.Schedule(
            date=int(date['day']),
            day=(calendar.weekday(year, month, day) + 1),
            start_time=None,
            end_time=None,


        )
    recurring_events = get_recurring_events(user_id)
    if recurring_events:
        for recurring_event_dict in recurring_events:
            recurring_event = dict_to_entities.dict_to_event(recurring_event_dict)
            if is_recurring_on_date(recurring_event, date):
                schedule.add_event(recurring_event)

    return schedule


def is_recurring_on_date(recurring_event, target_date):
    recurrence_pattern = recurring_event.recurring
    if recurrence_pattern == 'Every Day':
        return True
    else:
        first_appearance = datetime.strptime(recurring_event.first_appearance, "%Y-%m-%d")
        target_date = datetime.strptime(target_date, "%Y-%m-%d")
        if recurrence_pattern == 'Every Month':
            if first_appearance.day == target_date.day:
                return True

        else:
            delta_days = (target_date - first_appearance).days
            if recurrence_pattern == 'Every Week':
                return delta_days % 7 == 0

            elif recurrence_pattern == 'Every 2 Weeks':
                return delta_days % 14 == 0

    return False
