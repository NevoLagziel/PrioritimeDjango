from bson import ObjectId
from db_connection import db
from Prioritime.Model_Logic import calendar_objects
import calendar

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
    return result.modified_count > 0


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
    return result.modified_count > 0


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
    return result.modified_count > 0


# Function for adding a new event to a users database without checking collisions
def add_event(user_id, event, date):
    year = date.year
    month = date.month
    day = date.day

    if not year_exists(user_id, year):
        if not add_new_year(user_id, year):
            return False

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

    if result.modified_count > 0:
        if increment_event_count(user_id, year):
            return True

    return False


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
    return result.modified_count > 0


def get_recurring_events(user_id):
    user_id = ObjectId(user_id)
    recurring_events = users.find_one(
        {"_id": user_id},
        {
            "recurring_events": 1,
            "_id": 0,
        }
    )
    return recurring_events['recurring_events']


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


def update_event(user_id, event_id, date, updated_data):
    update_fields = {f"calendar.$[y].months.$[m].days.$[d].event_list.$[event].{key}": value for key, value in
                     updated_data.items()}

    result = users.update_one(
        {
            "_id": ObjectId(user_id),
            "calendar.year": date['year'],
            "calendar.months.month": date['month'],
            "calendar.months.days.date": date['day']
        },
        {"$set": update_fields},
        array_filters=[
            {"y.year": date['year']},
            {"m.month": date['month']},
            {"d.date": date['day']},
            {"event._id": event_id}
        ]
    )
    return result.modified_count > 0


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
        if decrement_event_count(user_id, int(date['year'])):
            if not check_empty_year(user_id, int(date['year'])):
                return True

            if delete_year(user_id, int(date['year'])):
                return True

    return False


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
    return result.modified_count > 0


def delete_task(user_id, task_id):
    user_id = ObjectId(user_id)
    result = users.update_one(
        {"_id": user_id},
        {"$pull": {"task_list": {"_id": task_id}}}
    )
    return result.modified_count > 0


def update_task(user_id, task_id, updated_data):
    user_id = ObjectId(user_id)
    update_fields = {f"task_list.$[task].{key}": value for key, value in updated_data.items()}
    print(update_fields)
    result = users.update_one(
        {"_id": ObjectId(user_id), "task_list._id": task_id},
        {"$set": update_fields},
        array_filters=[{"task._id": task_id}]
    )
    return result.modified_count > 0


def check_empty_year(user_id, year):
    user_id = ObjectId(user_id)
    event_count_zero = users.count_documents(
        {
            "_id": user_id,
            "calendar.year": year,
            "calendar.event_count": 0
        }
    )

    days_off_count_zero = users.count_documents(
        {
            "_id": user_id,
            "calendar.year": year,
            "calendar.days_off": 0
        }
    )
    return event_count_zero > 0 and days_off_count_zero > 0


def increment_event_count(user_id, year):
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
    return result.modified_count > 0


def decrement_event_count(user_id, year):
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
    return result.modified_count > 0


def update_preferences(user_id, preference):
    user_id = ObjectId(user_id)
    result = users.update_one(
        {'_id': user_id},
        {'$set': {'preferences.' + preference['name']: preference}}
    )
    return result.modified_count > 0


def find_preference(user_id, task_name):
    user_id = ObjectId(user_id)
    preference = users.find_one(
        {'_id': user_id},
        {
            f'preferences.{task_name}': 1,
            '_id': 0
        }
    )
    return preference['preferences']


def update_day_off(user_id, date, day_off):
    year = int(date['year'])
    month = int(date['month'])
    day = int(date['day'])

    year_exist = year_exists(user_id, year)

    if not year_exist:
        if day_off:
            if not add_new_year(user_id, year):
                return False

        else:
            return True

    user_id = ObjectId(user_id)
    result = users.update_one(
        {
            "_id": user_id,
            "calendar.year": year,
            "calendar.months.month": month,
            "calendar.months.days.date": day
        },
        {
            '$set': {
                "calendar.$[y].months.$[m].days.$[d].day_off": day_off
            }
        },
        array_filters=[
            {"y.year": year},
            {"m.month": month},
            {"d.date": day}
        ]
    )

    if not result.modified_count > 0:
        return False

    if day_off:
        if increment_day_off_count(user_id, year):
            return True
    else:
        if decrement_day_off_count(user_id, year):
            if check_empty_year(user_id, year):
                if delete_year(user_id, year):
                    return True
            else:
                return True

    return False


def increment_day_off_count(user_id, year):
    result = users.update_one(
        {
            "_id": user_id,
            "calendar.year": year
        },
        {
            "$inc": {
                "calendar.$.days_off": 1
            }
        }
    )
    return result.modified_count > 0


def decrement_day_off_count(user_id, year):
    result = users.update_one(
        {
            "_id": user_id,
            "calendar.year": year
        },
        {
            "$inc": {
                "calendar.$.days_off": -1
            }
        }
    )
    return result.modified_count > 0

# def add_event_to(user_id):
#     user_id = ObjectId(user_id)
#     event = calendar_objects.Event(
#         name='name',
#         description='description',
#         start_time='12',
#         end_time='13'
#     ).__dict__()
#     year = '2026'
#     month = '12'
#     day = '11'
#     result = users.update_one(
#         {'_id': user_id},
#         {'$addToSet': {'calendar_dict.'+year+'.'+month+"."+day+".event_list": event}}
#     )
#     return result.modified_count > 0


# def get_dict_schedule(user_id):
#     user_id = ObjectId(user_id)
#     year = '2027'
#     month = '10'
#     day = '2'
#
#     schedule_dict = users.aggregate([
#         {"$match": {"_id": user_id}},
#         {"$unwind": "$calendar_dict."+year+"."+month+"."+day},
#         {"$replaceRoot": {"newRoot": "$calendar_dict."+year+"."+month+"."+day}}
#     ])
#     schedule_dict = list(schedule_dict)
#     print(schedule_dict)
#     return schedule_dict[0]


# def calendar_as_dict(user_id):
#     user_id = ObjectId(user_id)
#     event_list = []
#     year = '2025'
#     calendar_dict = {
#         "event_count": 0,
#         '10':
#             {
#                 '1': {"event_list": event_list, "event_count": 0, "day": 7},
#                 '2': {"event_list": event_list, "event_count": 0, "day": 7},
#                 '3': {"event_list": event_list, "event_count": 0, "day": 7},
#             },
#         '11':
#             {
#                 '1': {"event_list": event_list, "event_count": 0, "day": 7},
#                 '2': {"event_list": event_list, "event_count": 0, "day": 7},
#                 '3': {"event_list": event_list, "event_count": 0, "day": 7},
#             },
#         '12':
#             {
#                 '1': {"event_list": event_list, "event_count": 0, "day": 7},
#                 '2': {"event_list": event_list, "event_count": 0, "day": 7},
#                 '3': {"event_list": event_list, "event_count": 0, "day": 7},
#             }
#
#     }
#     result = users.update_one(
#         {"_id": user_id},
#         {"$set": {"calendar_dict."+year: calendar_dict}}
#     )
#     year = '2024'
#     month = '10'
#     day = '2'
#     result = users.find_one(
#         {"_id": user_id},
#         {"calendar_dict."+year+"."+month+"."+day: 1}
#     )
#     print(result)
