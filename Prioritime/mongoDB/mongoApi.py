from bson import ObjectId
from db_connection import db
from . import mongo_utils

users = db['users']  # users collection


# returns if the user exists or not
def user_exists(user_id=None, email=None, session=None):
    user_exist = 0
    if user_id:
        user_exist = users.count_documents({'_id': ObjectId(user_id)}, session=session)
    elif email:
        user_exist = users.count_documents({'email': email}, session=session)
    return user_exist == 1


def create_user(user_data, session):
    result = users.insert_one(user_data, session=session)
    if not result:
        return False

    return result.inserted_id


def delete_user(user_id, session):
    result = users.delete_one({'_id': ObjectId(user_id)}, session=session)
    return result.deleted_count == 1


def does_email_confirmed(confirmation_token, session):
    result = users.find_one(
        {'confirmation_token': confirmation_token},
        {
            'email_confirmed': 1,
            '_id': 0,
        }
        , session=session)
    return result


def confirm_email(confirmation_token, session):
    result = users.update_one(
        {'confirmation_token': confirmation_token},
        {'$set': {'email_confirmed': True}}
        , session=session)
    return result.modified_count == 1


def get_user_info(user_id=None, email=None, fields=None, session=None):
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
        user_info = users.find_one({'_id': user_id}, projection, session=session)

    elif email:
        user_info = users.find_one({'email': email}, projection, session=session)

    return user_info


def check_email_can_be_changed(user_id, email, session):
    user_info = get_user_info(email=email, fields=['_id'], session=session)
    if user_info is not None:
        if user_info['_id'] != ObjectId(user_id):
            return False

    return True


def update_user_info(user_id, updated_data, session):
    user_id = ObjectId(user_id)
    update_fields = {f"{key}": value for key, value in updated_data.items() if value is not None and len(value) > 0}
    result = users.update_one(
        {'_id': user_id},
        {'$set': update_fields},
        session=session
    )
    return result.modified_count > 0


def get_calendar(user_id, session):
    user_id = ObjectId(user_id)
    full_calendar = users.find_one({"_id": user_id}, {'calendar': 1}, session=session)
    return full_calendar


def get_yearly_calendar(user_id, year, session):
    user_id = ObjectId(user_id)
    yearly_calendar = users.aggregate([
        {"$match": {"_id": user_id}},
        {"$unwind": "$calendar"},
        {"$match": {"calendar.year": year}},
        {"$replaceRoot": {"newRoot": "$calendar"}}
    ], session=session)

    yearly_calendar = list(yearly_calendar)
    if not yearly_calendar:
        return None

    return yearly_calendar[0]


def get_monthly_calendar(user_id, date, session):
    user_id = ObjectId(user_id)
    year = date.year
    month = date.month
    monthly_calendar = users.aggregate([
        {"$match": {"_id": user_id}},
        {"$unwind": "$calendar"},
        {"$match": {"calendar.year": year}},
        {"$unwind": "$calendar.months"},
        {"$match": {"calendar.months.month": month}},
        {"$replaceRoot": {"newRoot": "$calendar.months"}}
    ], session=session)
    monthly_calendar = list(monthly_calendar)
    if not monthly_calendar:
        return None

    return monthly_calendar[0]


# function for loading a daily schedule from the database as a dictionary
def get_schedule(user_id, date, session):
    year = date.year
    month = date.month
    day = date.day
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
    ], session=session)

    schedule = list(schedule)
    if not schedule:
        return None

    return schedule[0]


def update_schedule(user_id, date, schedule, session):
    user_id = ObjectId(user_id)
    year = date.year
    month = date.month
    day = date.day
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
        , session=session)
    return result.modified_count > 0


# not sure if needed
def add_new_year(user_id, year, session):
    user = ObjectId(user_id)
    yearly_calendar = mongo_utils.create_new_year(year)
    yearly_calendar_dict = yearly_calendar.__dict__()
    result = users.update_one(
        {"_id": user},
        {
            "$addToSet": {
                "calendar": yearly_calendar_dict
            }
        }
        , session=session)
    return result.modified_count > 0


# function for checking if a certain year is already presented in the database
def year_exists(user_id, year, session):
    user = ObjectId(user_id)
    year_count = users.count_documents({"_id": user, "calendar.year": year}, session=session)
    return year_count > 0


def delete_year(user_id, year, session):
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
        , session=session)
    return result.modified_count > 0


# Function for adding a new event to a users database without checking collisions
def add_event(user_id, event, date, session):
    year = date.year
    month = date.month
    day = date.day

    if not year_exists(user_id, year, session):
        if not add_new_year(user_id, year, session):
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
        , session=session)

    if result.modified_count > 0:
        if increment_event_count(user_id, year, session):
            return True

    return False


def add_recurring_event(user_id, event, session):
    user_id = ObjectId(user_id)
    event_dict = event.__dict__()
    result = users.update_one(
        {"_id": user_id},
        {
            "$addToSet": {
                "recurring_events": event_dict
            }
        }
        , session=session)
    return result.modified_count > 0


def get_recurring_events(user_id, session):
    user_id = ObjectId(user_id)
    recurring_events = users.find_one(
        {"_id": user_id},
        {
            "recurring_events": 1,
            "_id": 0,
        }
        , session=session)
    return recurring_events['recurring_events']


def get_event(user_id, date, event_id, session):
    user_id = ObjectId(user_id)
    year = date.year
    month = date.month
    day = date.day
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
    ], session=session)
    event_dict = list(event_dict)
    if not event_dict:
        return None

    return event_dict[0]


def update_event(user_id, event_id, date, updated_data, session):
    year = date.year
    month = date.month
    day = date.day
    update_fields = {f"calendar.$[y].months.$[m].days.$[d].event_list.$[event].{key}": value for key, value in
                     updated_data.items() if value is not None}

    result = users.update_one(
        {
            "_id": ObjectId(user_id),
            "calendar.year": year,
            "calendar.months.month": month,
            "calendar.months.days.date": day
        },
        {"$set": update_fields},
        array_filters=[
            {"y.year": year},
            {"m.month": month},
            {"d.date": day},
            {"event._id": event_id}
        ]
        , session=session)
    return result.modified_count > 0


def update_recurring_event(user_id, event_id, updated_data, session):
    user_id = ObjectId(user_id)
    update_fields = {f"recurring_events.$[event].{key}": value for key, value in updated_data.items() if
                     value is not None}
    result = users.update_one(
        {"_id": ObjectId(user_id), "recurring_events._id": event_id},
        {"$set": update_fields},
        array_filters=[{"event._id": event_id}]
        , session=session)
    return result.modified_count > 0


def delete_event(user_id, date, event_id, session):
    user_id = ObjectId(user_id)
    year = date.year
    month = date.month
    day = date.day
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
        , session=session)

    if result.modified_count > 0:
        if decrement_event_count(user_id, date.year, session=session):
            if not check_empty_year(user_id, date.year, session=session):
                return True

            if delete_year(user_id, date.year, session=session):
                return True

    return False


def delete_recurring_event(user_id, event_id, session):
    user_id = ObjectId(user_id)
    result = users.update_one(
        {"_id": user_id},
        {"$pull": {"recurring_events": {"_id": event_id}}}
        , session=session)
    return result.modified_count > 0


def get_task_list(user_id, session):  # returns tasks list as dictionary
    user_id = ObjectId(user_id)
    task_list = users.find_one(
        {"_id": user_id},
        {
            "task_list": 1,
            "_id": 0,
        }
        , session=session)
    return task_list


def add_task(user_id, task, session):
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
        , session=session)
    return result.modified_count > 0


def delete_task(user_id, task_id, session):
    user_id = ObjectId(user_id)
    result = users.update_one(
        {"_id": user_id},
        {"$pull": {"task_list": {"_id": task_id}}}
        , session=session)
    return result.modified_count > 0


def update_task(user_id, task_id, updated_data, session):
    user_id = ObjectId(user_id)
    update_fields = {f"task_list.$[task].{key}": value for key, value in updated_data.items() if value is not None}
    result = users.update_one(
        {"_id": ObjectId(user_id), "task_list._id": task_id},
        {"$set": update_fields},
        array_filters=[{"task._id": task_id}]
        , session=session)
    return result.modified_count > 0


def add_recurring_task(user_id, task, session):
    user_id = ObjectId(user_id)
    task_dict = task.__dict__()
    result = users.update_one(
        {"_id": user_id},
        {
            "$addToSet": {
                "recurring_tasks": task_dict
            }
        }
        , session=session)
    return result.modified_count > 0


def get_recurring_tasks(user_id, session):
    user_id = ObjectId(user_id)
    recurring_tasks = users.find_one(
        {"_id": user_id},
        {
            "recurring_tasks": 1,
            "_id": 0,
        }
        , session=session)
    return recurring_tasks


def update_recurring_task(user_id, task_id, updated_data, session):
    user_id = ObjectId(user_id)
    update_fields = {f"recurring_tasks.$[task].{key}": value for key, value in updated_data.items()}
    result = users.update_one(
        {"_id": ObjectId(user_id), "recurring_tasks._id": task_id},
        {"$set": update_fields},
        array_filters=[{"task._id": task_id}]
        , session=session)
    return result.modified_count > 0


def delete_recurring_task(user_id, task_id, session):
    user_id = ObjectId(user_id)
    result = users.update_one(
        {"_id": user_id},
        {"$pull": {"recurring_tasks": {"_id": task_id}}}
        , session=session)
    return result.modified_count > 0


def check_empty_year(user_id, year, session):
    user_id = ObjectId(user_id)
    event_count_zero = users.count_documents(
        {
            "_id": user_id,
            "calendar.year": year,
            "calendar.event_count": 0
        }
        , session=session)

    days_off_count_zero = users.count_documents(
        {
            "_id": user_id,
            "calendar.year": year,
            "calendar.days_off": 0
        }
        , session=session)
    return event_count_zero > 0 and days_off_count_zero > 0


def increment_event_count(user_id, year, session):
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
        , session=session)
    return result.modified_count > 0


def decrement_event_count(user_id, year, session):
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
        , session=session)
    return result.modified_count > 0


def get_preferences(user_id, session):
    user_id = ObjectId(user_id)
    preferences = users.find_one(
        {'_id': user_id},
        {
            'preferences': 1,
            '_id': 0
        }
        , session=session)
    return preferences['preferences']


def update_preferences(user_id, preference_manager, session):
    user_id = ObjectId(user_id)
    result = users.update_one(
        {'_id': user_id},
        {'$set': {'user_preferences': preference_manager.__dict__()}}
        , session=session)
    return result.modified_count > 0


def delete_preference(user_id, preference, session):
    user_id = ObjectId(user_id)
    result = users.delete_one(
        {'_id': user_id},
        {f'preferences.{preference}'}
        , session=session)
    return result.modified_count > 0


def get_user_preferences(user_id, session):
    user_id = ObjectId(user_id)
    user_preferences = users.find_one(
        {'_id': user_id},
        {
            'user_preferences': 1,
            '_id': 0
        },
        session=session
    )
    return user_preferences['user_preferences']


def find_preferences(user_id, fields, session):
    find_fields = {f'user_preferences.{field}': 1 for field in fields}
    user_id = ObjectId(user_id)
    preference = users.find_one(
        {'_id': user_id},
        find_fields
        , session=session)
    return preference['user_preferences']


def update_day_off(user_id, date, day_off, session):
    year = date.year
    month = date.month
    day = date.day

    year_exist = year_exists(user_id, year, session)

    if not year_exist:
        if day_off:
            if not add_new_year(user_id, year, session):
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
        , session=session)

    if not result.modified_count > 0:
        return False

    if day_off:
        if increment_day_off_count(user_id, year, session):
            return True
    else:
        if decrement_day_off_count(user_id, year, session):
            if check_empty_year(user_id, year, session):
                if delete_year(user_id, year, session):
                    return True
            else:
                return True

    return False


def increment_day_off_count(user_id, year, session):
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
        , session=session)
    return result.modified_count > 0


def decrement_day_off_count(user_id, year, session):
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
        , session=session)
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
