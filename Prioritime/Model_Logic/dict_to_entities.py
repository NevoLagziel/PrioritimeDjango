from Prioritime.Model_Logic import calendar_objects
from Prioritime.mongoDB import mongoApi


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


def create_new_task(user_id, data):
    # must have at least a name
    if 'name' not in data:
        return None

    name = data.get('name')  # string
    status = data.get('status')  # filled by default
    if len(data.keys()) == 2:
        preference = mongoApi.find_preference(user_id, name)
        if preference:
            preference = preference[name]
            # crating task by the data in the preferences
            fields = dict(preference['fields'])
            task = calendar_objects.Task(name=name, status=status, **fields)
        else:
            # creating task with only name
            task = calendar_objects.Task(name=name, status=status)
    else:
        # creating task by the data entered by the user
        task = calendar_objects.Task(
            name=name,
            description=data.get('description'),
            duration=data.get('duration'),
            frequency=data.get('frequency'),
            category=data.get('category'),
            tags=data.get('tags'),
            # reminders=reminders,
            location=data.get('location'),
            # priority=priority,
            deadline=data.get('deadline'),
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
        name=data.get('name'),
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
