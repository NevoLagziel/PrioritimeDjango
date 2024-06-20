from ..Model_Logic import calendar_objects, user_preferences
from ..mongoDB import mongoApi
from ..utils import is_iso_date


# From mongodb #
def dict_to_task(task_dict):
    task = calendar_objects.Task(**task_dict)
    # task = calendar_objects.Task(
    #     _id=task_dict["_id"],
    #     name=task_dict["name"],
    #     description=task_dict["description"],
    #     duration=task_dict["duration"],
    #     category=task_dict["category"],
    #     tags=task_dict["tags"],
    #     reminders=task_dict["reminders"],
    #     location=task_dict["location"],
    #     recurring = task_dict["recurring"],
    #     creation_date=task_dict["creation_date"],
    #     priority=task_dict["priority"],
    #     deadline=task_dict["deadline"],
    #     status=task_dict["status"],
    # )
    return task


def dict_to_event(event_dict):
    event = calendar_objects.Event(**event_dict)
    # event = calendar_objects.Event(
    #     _id=event_dict["_id"],
    #     name=event_dict["name"],
    #     description=event_dict["description"],
    #     duration=event_dict["duration"],
    #     category=event_dict["category"],
    #     tags=event_dict["tags"],
    #     reminders=event_dict["reminders"],
    #     location=event_dict["location"],
    #     recurring=event_dict["recurring"],
    #     creation_date=event_dict["creation_date"],
    #     first_appearance=event_dict["first_appearance"],
    #     start_time=event_dict["start_time"],
    #     end_time=event_dict["end_time"],
    #     sub_event=event_dict["sub_event"],
    # )
    return event


def dict_to_task_list(task_list_dict):
    task_list = calendar_objects.Tasks([dict_to_task(task_dict) for task_dict in task_list_dict])
    return task_list


def dict_to_schedule(schedule_dict):
    event_list_dict = schedule_dict['event_list']
    event_list = []
    if event_list_dict:
        for event_dict in event_list_dict:
            if event_dict['item_type'] == 'task':
                event = dict_to_task(event_dict)
            else:
                event = dict_to_event(event_dict)
            event_list.append(event)

    schedule = calendar_objects.Schedule(
        date=schedule_dict['date'],
        day=schedule_dict['day'],
        start_time=schedule_dict['start_time'],
        end_time=schedule_dict['end_time'],
        event_list=event_list,
        day_off=schedule_dict['day_off']
    )
    return schedule


def dict_to_monthly_calendar(monthly_calendar_dict):
    schedule_list = []
    for schedule_dict in monthly_calendar_dict['days']:
        schedule = dict_to_schedule(schedule_dict)
        schedule_list.append(schedule)

    monthly_calendar = calendar_objects.MonthlyCalendar(
        month=monthly_calendar_dict['month'],
        number_of_days=monthly_calendar_dict['number_of_days'],
        starting_day=monthly_calendar_dict['starting_day'],
        list_of_schedules=schedule_list
    )
    return monthly_calendar


# From the frontend #

def create_new_task(user_id, data, session):
    # must have at least a name
    auto_fill = True
    name = data.get('name').replace('.', '')  # string
    status = data.get('status')  # filled by default
    frequency = data.get('frequency')  # filled by default
    def_keys = ['name', 'status', 'frequency', 'type']
    if 'name' not in data:
        return None

    for key in data.keys():
        if key not in def_keys and data.get(key):
            auto_fill = False

    if frequency != 'Once' and frequency is not None:
        auto_fill = False

    if auto_fill:
        preferences_dict = mongoApi.get_user_preferences(user_id, session=session)
        preference_manager = user_preferences.PreferenceManager(**preferences_dict)
        preference = preference_manager.find_matching_preference(name)
        if preference:
            fields = preference.fields
            task = calendar_objects.Task(name=name, status=status, **fields)
        else:
            # creating task with only name
            task = calendar_objects.Task(name=name, status=status)
    else:
        # creating task by the data entered by the user
        deadline = data.get('deadline') or data.get('selectedDateTime')
        if deadline:
            deadline = deadline.split('.')[0]

        task = calendar_objects.Task(
            name=name,
            description=data.get('description') or data.get('details'),
            duration=data.get('duration'),
            frequency=frequency,
            category=data.get('category') or data.get('selectedCategory'),
            tags=data.get('tags'),
            reminders=data.get('reminders'),
            location=data.get('location'),
            priority=data.get('priority'),
            deadline=deadline,
            status=status,
        )

    return task


def create_new_event(data):
    keys = set(data.keys())
    necessary_data = {'name', 'start_time', 'end_time'}
    if not necessary_data.issubset(keys):
        return None

    event = calendar_objects.Event(
        _id=data.get('_id'),
        name=data.get('name').replace('.', ''),
        description=data.get('description'),
        duration=data.get('duration'),
        frequency=data.get('frequency'),
        category=data.get('category'),
        tags=data.get('tags'),
        reminders=data.get('reminders'),
        location=data.get('location'),
        start_time=data.get('start_time'),
        end_time=data.get('end_time'),
        sub_event=data.get('sub_event'),
    )
    return event


def organize_data_edit_event(data):
    organized_data = {
        '_id': data.get('id') or data.get('_id'),
        'name': data.get('title') or data.get('name'),
        'start_time': data.get('start') or data.get('start_time'),
        'end_time': data.get('end') or data.get('end_time'),
        'category': data.get('category'),
        'tags': data.get('tags'),
        'duration': data.get('duration'),
        'item_type': data.get('type') or data.get('item_type'),
        'description': data.get('description'),
        'location': data.get('location'),
        'frequency': data.get('frequency'),
        'reminders': data.get('reminders'),
        'creation_date': data.get('creation_date'),
        'sub_event': data.get('sub_event')
    }
    if organized_data.get('start_time'):
        organized_data['start_time'] = organized_data.get('start_time').split('.')[0]

    if organized_data.get('end_time'):
        organized_data['end_time'] = organized_data.get('end_time').split('.')[0]

    if organized_data.get('name'):
        organized_data['name'] = organized_data.get('name').replace('.', '')

    return organized_data


def organize_data_edit_task(data):
    organized_data = {
        '_id': data.get('id') or data.get('_id'),
        'name': data.get('title') or data.get('name'),
        'category': data.get('category'),
        'tags': data.get('tags'),
        'duration': data.get('duration'),
        'item_type': data.get('type') or data.get('item_type'),
        'description': data.get('description'),
        'location': data.get('location'),
        'frequency': data.get('frequency'),
        'creation_date': data.get('creation_date'),
        'deadline': data.get('deadline') if is_iso_date(data.get('deadline')) else None,
        'status': data.get('status'),
        'priority': data.get('priority'),
        'reminders': data.get('reminders'),
    }
    if organized_data.get('name'):
        organized_data['name'] = organized_data.get('name').replace('.', '')

    return organized_data


# def dict_to_preferences(data):
#     copy_data = data.copy()
#     preferences = data.get('preferences')
#     start_time = data.get('start_time')
#     end_time = data.get('end_time')
#
#     if start_time is not None and len(start_time) == 5:
#         start_time = f"{start_time}:00"
#     if end_time is not None and len(start_time) == 5:
#         end_time = f"{end_time}:00"
#
#     copy_data['start_time'] = start_time
#     copy_data['end_time'] = end_time
#
#     preference_manager = user_preferences.PreferenceManager(
#         days_off=data.get('days_off'),
#         start_time=start_time,
#         end_time=end_time
#     )
#     for pref in preferences:
#         preference_manager.add_preference(
#             name=pref.get('name'),
#             days=pref.get('days'),
#             daytime=pref.get('daytime'),
#             duration=pref.get('duration'),
#         )
#
#     return preference_manager

def dict_to_preferences(data):
    copy_data = data.copy()
    start_time = data.get('start_time')
    end_time = data.get('end_time')

    if start_time is not None and len(start_time) == 5:
        start_time = f"{start_time}:00"
    if end_time is not None and len(end_time) == 5:
        end_time = f"{end_time}:00"

    copy_data['start_time'] = start_time
    copy_data['end_time'] = end_time

    preference_manager = user_preferences.PreferenceManager(**copy_data)
    return preference_manager
