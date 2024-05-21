from Prioritime import calendar_objects


def dict_to_task(task_dict):
    task = calendar_objects.Task(
        _id=task_dict["_id"],
        name=task_dict["name"],
        description=task_dict["description"],
        duration=task_dict["duration"],
        category=task_dict["category"],
        tags=task_dict["tags"],
        reminders=task_dict["reminders"],
        location=task_dict["location"],
        recurring = task_dict["recurring"],
        creation_date=task_dict["creation_date"],
        priority=task_dict["priority"],
        deadline=task_dict["deadline"],
        status=task_dict["status"],
    )
    return task


def dict_to_event(event_dict):
    event = calendar_objects.Event(
        _id=event_dict["_id"],
        name=event_dict["name"],
        description=event_dict["description"],
        duration=event_dict["duration"],
        category=event_dict["category"],
        tags=event_dict["tags"],
        reminders=event_dict["reminders"],
        location=event_dict["location"],
        recurring=event_dict["recurring"],
        creation_date=event_dict["creation_date"],
        first_appearance=event_dict["first_appearance"],
        start_time=event_dict["start_time"],
        end_time=event_dict["end_time"],
        sub_event=event_dict["sub_event"],
    )
    return event


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
