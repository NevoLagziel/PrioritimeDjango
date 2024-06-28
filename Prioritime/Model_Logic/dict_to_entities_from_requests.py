from ..Model_Logic import calendar_objects, user_preferences
from ..mongoDB import mongoApi
from ..utils import is_iso_date

frequency_options = ['Once', 'Every Day', 'Every Week', 'Every 2 Weeks', 'Every Month']


def create_new_task(user_id, data, session):
    # must have at least a name
    auto_fill = True
    name = data.get('name').replace('.', '')  # string
    status = data.get('status')  # filled by default
    frequency = data.get('frequency')  # filled by default
    frequency = frequency if frequency in frequency_options else 'Once'
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
        frequency=data.get('frequency') if data.get('frequency') in frequency_options else 'Once',
        category=data.get('category'),
        tags=data.get('tags'),
        reminders=data.get('reminders'),
        location=data.get('location'),
        start_time=data.get('start_time'),
        end_time=data.get('end_time'),
        sub_event=data.get('sub_event'),
    )

    if event.start_time > event.end_time:
        return None

    return event


def organize_data_edit_event(data):
    frequency = data.get('frequency')
    frequency = frequency if frequency in frequency_options else 'Once'
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
        'frequency': frequency,
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
        'creation_date': data.get('creation_date'),
        'deadline': data.get('deadline') if is_iso_date(data.get('deadline')) else None,
        'status': data.get('status'),
        'priority': data.get('priority'),
        'reminders': data.get('reminders'),
    }
    if organized_data.get('name'):
        organized_data['name'] = organized_data.get('name').replace('.', '')

    if organized_data.get('deadline'):
        organized_data['deadline'] = organized_data.get('deadline').split('.')[0]

    return organized_data


def organize_data_edit_user_info(data):
    organized_data = {
        'email': data.get('email'),
        'firstName': data.get('firstName'),
        'lastName': data.get('lastName')
    }
    return organized_data


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
