from ..Model_Logic import calendar_objects, user_preferences
from ..mongoDB import mongoApi
from ..utils import is_iso_date

frequency_options = ['Once', 'Every Day', 'Every Week', 'Every 2 Weeks', 'Every Month']


# def create_new_task(user_id, data, session):
#     auto_fill = True
#     def_keys = ['name', 'status', 'frequency', 'type']
#     if 'name' not in data:
#         return None
#
#     name = data.get('name').replace('.', '')  # string
#     status = data.get('status')  # filled by default
#     frequency = data.get('frequency')  # filled by default
#     frequency = frequency if frequency in frequency_options else 'Once'
#
#     for key in data.keys():
#         if key not in def_keys and data.get(key):
#             auto_fill = False
#
#     if frequency != 'Once' and frequency is not None:
#         auto_fill = False
#
#     if auto_fill:
#         preferences_dict = mongoApi.get_user_preferences(user_id, session=session)
#         preference_manager = user_preferences.PreferenceManager(**preferences_dict)
#         preference = preference_manager.find_matching_preference(name)
#         if preference:
#             fields = preference.fields
#             task = calendar_objects.Task(name=name, status=status, **fields)
#         else:
#             task = calendar_objects.Task(name=name, status=status)
#     else:
#         # creating task by the data entered by the user
#         deadline = data.get('deadline') or data.get('selectedDateTime')
#         if deadline:
#             deadline = deadline.split('.')[0]
#
#         task = calendar_objects.Task(
#             name=name,
#             description=data.get('description') or data.get('details'),
#             duration=data.get('duration'),
#             frequency=frequency,
#             category=data.get('category') or data.get('selectedCategory'),
#             tags=data.get('tags'),
#             reminders=data.get('reminders'),
#             location=data.get('location'),
#             priority=data.get('priority'),
#             deadline=deadline,
#             status=status,
#         )
#
#     return task


def create_new_task(user_id, data, session):
    # To check if only name entered to be filled by preference data
    data = organize_entered_data_calendar_objects(data=data, task=True)
    auto_fill = True
    def_keys = ['name', 'status', 'frequency', 'item_type']

    # Name must be filled
    if not data.get('name'):
        return None

    name = data.get('name').replace('.', '')
    status = data.get('status')  # filled by default

    # Checking if other fields other than default been filled
    for key in data.keys():
        if key not in def_keys and data.get(key):
            auto_fill = False

    # Check if recurring task, so it wouldn't be filled by preference
    if data.get('frequency') != 'Once':
        auto_fill = False

    if auto_fill:
        preferences_dict = mongoApi.get_user_preferences(user_id, session=session)
        preference_manager = user_preferences.PreferenceManager(**preferences_dict)
        preference = preference_manager.find_matching_preference(name)
        if preference:
            fields = preference.fields
            task = calendar_objects.Task(name=name, status=status, **fields)
            return task

    task = calendar_objects.Task(**data)
    return task

# def create_new_event(data):
#     keys = set(data.keys())
#     necessary_data = {'name', 'start_time', 'end_time'}
#     if not necessary_data.issubset(keys):
#         return None
#
#     event = calendar_objects.Event(
#         _id=data.get('_id'),
#         name=data.get('name').replace('.', ''),
#         description=data.get('description'),
#         duration=data.get('duration'),
#         frequency=data.get('frequency') if data.get('frequency') in frequency_options else 'Once',
#         category=data.get('category'),
#         tags=data.get('tags'),
#         reminders=data.get('reminders'),
#         location=data.get('location'),
#         start_time=data.get('start_time'),
#         end_time=data.get('end_time'),
#         sub_event=data.get('sub_event'),
#     )
#
#     if event.start_time > event.end_time or event.start_time.date() != event.end_time.date():
#         return None
#
#     return event


# Checking that necessary data received and creating object
def create_new_event(data):
    necessary_data = ['name', 'start_time', 'end_time']
    data = organize_entered_data_calendar_objects(data=data, event=True)

    for key in necessary_data:
        if not data[key]:
            return None

    event = calendar_objects.Event(**data)
    if event.start_time > event.end_time or event.start_time.date() != event.end_time.date():
        return None

    return event


# Organizing the data for events and tasks sent by the frontend request
def organize_entered_data_calendar_objects(data, event=None, task=None):
    frequency = data.get('frequency')
    frequency = frequency if frequency in frequency_options else 'Once'
    organized_data = {
        '_id': data.get('id') or data.get('_id'),
        'name': data.get('title') or data.get('name'),
        'category': data.get('category'),
        'tags': data.get('tags'),
        'duration': data.get('duration'),
        'item_type': data.get('type') or data.get('item_type'),
        'description': data.get('description'),
        'location': data.get('location'),
        'frequency': frequency,
        'reminders': data.get('reminders'),
    }
    if event:
        organized_data['start_time'] = data.get('start') or data.get('start_time')
        organized_data['end_time'] = data.get('end') or data.get('end_time')
        # Removing time zone if sent
        if organized_data.get('start_time'):
            organized_data['start_time'] = organized_data.get('start_time').split('.')[0]

        if organized_data.get('end_time'):
            organized_data['end_time'] = organized_data.get('end_time').split('.')[0]

    elif task:
        organized_data['deadline'] = data.get('deadline') if is_iso_date(data.get('deadline')) else None
        organized_data['status'] = data.get('status')
        organized_data['priority'] = data.get('priority')
        # Removing time zone if sent
        if organized_data.get('deadline'):
            organized_data['deadline'] = organized_data.get('deadline').split('.')[0]

    # Making sure name is without "." for being stored in the database
    if organized_data.get('name'):
        organized_data['name'] = organized_data.get('name').replace('.', '')

    return organized_data


# def organize_data_edit_event(data):
#     frequency = data.get('frequency')
#     frequency = frequency if frequency in frequency_options else 'Once'
#     organized_data = {
#         '_id': data.get('id') or data.get('_id'),
#         'name': data.get('title') or data.get('name'),
#         'start_time': data.get('start') or data.get('start_time'),
#         'end_time': data.get('end') or data.get('end_time'),
#         'category': data.get('category'),
#         'tags': data.get('tags'),
#         'duration': data.get('duration'),
#         'item_type': data.get('type') or data.get('item_type'),
#         'description': data.get('description'),
#         'location': data.get('location'),
#         'frequency': frequency,
#         'reminders': data.get('reminders'),
#         'sub_event': data.get('sub_event')
#     }
#     if organized_data.get('start_time'):
#         organized_data['start_time'] = organized_data.get('start_time').split('.')[0]
#
#     if organized_data.get('end_time'):
#         organized_data['end_time'] = organized_data.get('end_time').split('.')[0]
#
#     # Making sure name is without "." for being stored in the database
#     if organized_data.get('name'):
#         organized_data['name'] = organized_data.get('name').replace('.', '')
#
#     return organized_data
#
#
# def organize_data_edit_task(data):
#     frequency = data.get('frequency')
#     frequency = frequency if frequency in frequency_options else 'Once'
#     organized_data = {
#         '_id': data.get('id') or data.get('_id'),
#         'name': data.get('title') or data.get('name'),
#         'category': data.get('category'),
#         'tags': data.get('tags'),
#         'duration': data.get('duration'),
#         'item_type': data.get('type') or data.get('item_type'),
#         'description': data.get('description'),
#         'location': data.get('location'),
#         'frequency': frequency,
#         'deadline': data.get('deadline') if is_iso_date(data.get('deadline')) else None,
#         'status': data.get('status'),
#         'priority': data.get('priority'),
#         'reminders': data.get('reminders'),
#     }
#     # Making sure name is without "." for being stored in the database
#     if organized_data.get('name'):
#         organized_data['name'] = organized_data.get('name').replace('.', '')
#
#     if organized_data.get('deadline'):
#         organized_data['deadline'] = organized_data.get('deadline').split('.')[0]
#
#     return organized_data


# Organize the data sent for user info
def organize_data_edit_user_info(data):
    organized_data = {
        'email': data.get('email'),
        'firstName': data.get('firstName'),
        'lastName': data.get('lastName')
    }
    return organized_data


# Checking and creating preferences by the data sent by frontend
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
