from ..Model_Logic import calendar_objects


# From mongodb #
def dict_to_task(task_dict):
    task = calendar_objects.Task(**task_dict)
    return task


def dict_to_event(event_dict):
    event = calendar_objects.Event(**event_dict)
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
