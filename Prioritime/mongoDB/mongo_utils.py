from . import mongoApi
from Prioritime.Model_Logic import dict_to_entities, calendar_objects
import calendar
from datetime import datetime, timedelta


def create_new_year(year):
    list_of_monthly_calendars = []
    for month in range(1, 13):
        list_of_monthly_calendars.append(create_new_month(year, month))

    yearly_calendar = calendar_objects.YearlyCalendar(
        year=year,
        list_of_monthly_calendars=list_of_monthly_calendars
    )
    return yearly_calendar


def create_new_month(year, month):
    list_of_schedules = []
    num_of_days = calendar.monthrange(year, month)[1]
    for day in range(1, num_of_days + 1):
        list_of_schedules.append(create_new_schedule(year, month, day))

    monthly_calendar = calendar_objects.MonthlyCalendar(
        month=month,
        number_of_days=num_of_days,
        starting_day=((calendar.monthrange(year, month)[0] + 1) % 7),
        list_of_schedules=list_of_schedules
    )
    return monthly_calendar


def create_new_schedule(year, month, day):
    schedule = calendar_objects.Schedule(
        date=day,
        day=((calendar.weekday(year, month, day) + 1) % 7),
    )
    return schedule


def get_monthly_calendar(user_id, date, session):
    month = date.month
    year = date.year
    monthly_calendar_dict = mongoApi.get_monthly_calendar(user_id, date, session=session)
    if monthly_calendar_dict:
        monthly_calendar = dict_to_entities.dict_to_monthly_calendar(monthly_calendar_dict)
    else:
        monthly_calendar = create_new_month(year, month)

    recurring_events = mongoApi.get_recurring_events(user_id, session=session)
    if recurring_events is None:
        return None

    # task_list_dict = task_list_dict['task_list']
    if not recurring_events:
        return monthly_calendar

    # tasks = dict_to_entities.dict_to_task_list(task_list_dict) if task_list_dict else None
    for schedule in monthly_calendar.list_of_schedules:
        datetime_date = datetime(year=year, month=month, day=schedule.date)
        if recurring_events:
            insert_recurring_events_to_schedule(recurring_events, schedule, datetime_date)

        # remove that if updating the tasks to be in a schedule
        # if tasks:
        #     insert_scheduled_tasks_to_schedule(tasks, schedule, datetime_date)
    return monthly_calendar


def get_schedule(user_id, date, session):
    year = date.year
    month = date.month
    day = date.day
    schedule_dict = mongoApi.get_schedule(user_id, date, session=session)
    if schedule_dict:
        schedule = dict_to_entities.dict_to_schedule(schedule_dict)
    else:
        schedule = create_new_schedule(year, month, day)

    recurring_events = mongoApi.get_recurring_events(user_id, session=session)
    if recurring_events is None:
        return None

    insert_recurring_events_to_schedule(recurring_events, schedule, date)

    # remove that if updating the tasks to be in a schedule
    # task_list_dict = get_task_list(user_id, session=session)
    # if task_list_dict is None:
    #     return None
    #
    # if task_list_dict:
    #     tasks = dict_to_entities.dict_to_task_list(task_list_dict['task_list'])
    #     insert_scheduled_tasks_to_schedule(tasks, schedule, date)

    return schedule


def get_date_range_schedules(user_id, start_date, end_date, session):
    if start_date > end_date:
        return None

    schedules = {}
    current_date = start_date
    while current_date <= end_date:
        schedule = get_schedule(user_id, current_date, session=session)
        if schedule is None:
            return None

        schedules[str(current_date.date())] = schedule.__dict__()
        current_date = current_date + timedelta(days=1)

    return schedules


def insert_recurring_events_to_schedule(recurring_events, schedule, date):
    for recurring_event_dict in recurring_events:
        recurring_event = dict_to_entities.dict_to_event(recurring_event_dict)
        if is_recurring_on_date(recurring_event, date):
            recurring_event.start_time = recurring_event.start_time.replace(year=date.year, month=date.month,
                                                                            day=date.day)

            recurring_event.end_time = recurring_event.end_time.replace(year=date.year, month=date.month, day=date.day)

            schedule.add_event(recurring_event)


def insert_scheduled_tasks_to_schedule(tasks, schedule, date):
    filtered_tasks = tasks.filter_by(status='scheduled', date=date)
    if filtered_tasks:
        for task in filtered_tasks:
            schedule.add_event(task)


def is_recurring_on_date(recurring_event, target_date):
    recurrence_pattern = recurring_event.frequency
    if recurrence_pattern == 'Every Day':
        return True
    else:
        first_appearance = recurring_event.first_appearance
        if recurrence_pattern == 'Every Month':
            if first_appearance.day == target_date.day:
                return True
            else:
                num_of_days = calendar.monthrange(target_date.year, target_date.month)[1]
                if target_date.day == num_of_days and num_of_days <= first_appearance.day:
                    return True

        else:
            first_appearance = datetime(year=first_appearance.year, month=first_appearance.month,
                                        day=first_appearance.day)
            delta_days = (target_date - first_appearance).days
            if recurrence_pattern == 'Every Week':
                return delta_days % 7 == 0

            elif recurrence_pattern == 'Every 2 Weeks':
                return delta_days % 14 == 0

    return False


# def update_event_2(user_id, old_date, new_date, event_id, updated_data, session):
#     item_type = updated_data.get('item_type')
#     if item_type == 'recurring event':
#         new_updated_data = updated_data.copy()
#         if old_date.date() != new_date.date():
#             new_updated_data['first_appearance'] = new_date.isoformat()
#
#         if mongoApi.update_recurring_event(user_id, event_id, new_updated_data, session=session):
#             return True
#
#     else:
#         if old_date.date() == new_date.date():
#             if mongoApi.update_event(user_id, event_id, old_date, updated_data, session=session):
#                 return True
#         else:
#             updated_event = dict_to_entities.create_new_event(updated_data)
#             if mongoApi.delete_event(user_id, old_date, event_id, session=session):
#                 if mongoApi.add_event(user_id, updated_event, new_date, session=session):
#                     return True
#
#     return False


def update_event(user_id, old_date, new_date, event_id, updated_data, session):
    item_type = updated_data.get('item_type')
    if item_type == 'recurring event':
        if updated_data.get('frequency') == 'Once':
            event_dict = get_recurring_event(user_id, event_id, session=session)
            if event_dict is None:
                return False

            event_dict.update(updated_data)
            event_dict['item_type'] = 'event'
            event = dict_to_entities.dict_to_event(event_dict)
            if mongoApi.delete_recurring_event(user_id, event_id, session=session):
                if mongoApi.add_event(user_id, event, new_date, session=session):
                    return True

        else:
            updated_data['first_appearance'] = new_date.isoformat()

            if mongoApi.update_recurring_event(user_id, event_id, updated_data, session=session):
                return True

    else:
        change_to_recurring = False if updated_data.get('frequency') == 'Once' or updated_data.get(
            'frequency') is None else True
        if old_date.date() == new_date.date() and not change_to_recurring:
            if mongoApi.update_event(user_id, event_id, old_date, updated_data, session=session):
                return True

        else:
            event_dict = mongoApi.get_event(user_id, old_date, event_id, session=session)
            if event_dict is None:
                return False

            event_dict.update(updated_data)
            if event_dict.get('item_type') == 'task':
                event = dict_to_entities.dict_to_task(event_dict)
            else:
                event = dict_to_entities.dict_to_event(event_dict)

            if mongoApi.delete_event(user_id, old_date, event_id, session=session):
                if change_to_recurring:
                    event.first_appearance = event.start_time
                    event.item_type = 'recurring event'
                    if mongoApi.add_recurring_event(user_id, event, session=session):
                        return True
                else:
                    if mongoApi.add_event(user_id, event, new_date, session=session):
                        return True

    return False


def update_task(user_id, task_id, updated_data, session):
    item_type = updated_data.get('item_type')
    if item_type == 'recurring task':
        task_dict = get_recurring_task(user_id, task_id, session=session)
        if task_dict is None:
            return False

        mongoApi.delete_task(user_id=user_id, task_id=task_dict['last_instance'], session=session)
        updated_data['last_instance'] = None
        updated_data['previous_done'] = None

        if updated_data.get('frequency') == 'Once':
            task_dict.update(updated_data)
            task_dict['item_type'] = 'task'
            task = dict_to_entities.dict_to_task(task_dict)
            if mongoApi.delete_recurring_task(user_id, task_id, session=session):
                if mongoApi.add_task(user_id, task, session=session):
                    return True

        else:
            if mongoApi.update_recurring_task(user_id, task_id, updated_data, session=session):
                return True

    else:
        if updated_data.get('frequency') == 'Once' or (not updated_data.get('frequency')):
            if mongoApi.update_task(user_id, task_id, updated_data, session=session):
                return True

        else:
            task_dict = get_task(user_id, task_id, session=session)
            if task_dict is None:
                return False

            mongoApi.delete_task(user_id=user_id, task_id=task_dict['last_instance'], session=session)
            updated_data['last_instance'] = None
            updated_data['previous_done'] = None
            task_dict.update(updated_data)
            task = dict_to_entities.dict_to_task(task_dict)
            task.item_type = 'recurring task'
            task.previous_done = None
            if mongoApi.delete_task(user_id, task_id, session=session):
                if mongoApi.add_recurring_task(user_id, task, session=session):
                    return True

        return False


def get_task_list(user_id, deadline=None, session=None):
    if not insert_recurring_tasks_to_task_list(user_id, session=session):
        return None

    task_list_dict = mongoApi.get_task_list(user_id, session=session)
    if task_list_dict is None:
        return None

    if not deadline:
        return task_list_dict

    task_list = dict_to_entities.dict_to_task_list(task_list_dict['task_list'])
    filtered_task_list = calendar_objects.Tasks(task_list.get_list_by_deadline(deadline))
    return filtered_task_list.__dict__()


def insert_recurring_tasks_to_task_list(user_id, session):
    recurring_tasks_dict = mongoApi.get_recurring_tasks(user_id, session=session)
    if recurring_tasks_dict is None:
        return False

    recurring_tasks_dict = recurring_tasks_dict['recurring_tasks']
    if not recurring_tasks_dict:
        return True

    current_date = datetime(year=datetime.now().year, month=datetime.now().month, day=datetime.now().day)
    recurring_tasks = dict_to_entities.dict_to_task_list(recurring_tasks_dict)
    for recurring_task in recurring_tasks.list_of_tasks:
        if recurring_task.previous_done is None or recurring_task.previous_done < current_date:
            if recurring_task.last_instance:
                mongoApi.delete_task(user_id=user_id, task_id=recurring_task.last_instance, session=session)

            deadline = find_deadline_for_next_recurring_task(recurring_task, current_date)
            new_task = recurring_task.generate_recurring_instance(deadline)
            if mongoApi.add_task(user_id, new_task, session=session):
                update_recurring_task = {'previous_done': deadline.isoformat(), 'last_instance': recurring_task.last_instance}
                if not mongoApi.update_recurring_task(user_id, recurring_task.id(), update_recurring_task, session=session):
                    return False
            else:
                return False

    return True


# works for a week from Sunday to Saturday and not Monday to Sunday
def find_deadline_for_next_recurring_task(recurring_task, current_date):
    deadline = None
    recurrence_pattern = recurring_task.frequency
    if recurrence_pattern == 'Every Day':
        deadline = current_date + timedelta(hours=23, minutes=59, seconds=59)
    elif recurrence_pattern == 'Every Week':
        week_start = current_date - timedelta(days=(current_date.weekday() + 1) % 7)
        deadline = week_start + timedelta(days=6, hours=23, minutes=59, seconds=59)
    elif recurrence_pattern == 'Every 2 Weeks':
        week_start = current_date - timedelta(days=(current_date.weekday() + 1) % 7)
        deadline = week_start + timedelta(days=13, hours=23, minutes=59, seconds=59)
    elif recurrence_pattern == 'Every Month':
        deadline = datetime(
            year=current_date.year,
            month=current_date.month,
            day=calendar.monthrange(current_date.year, current_date.month)[1],
            hour=23,
            minute=59,
            second=59,
        )
    return deadline


def get_recurring_event(user_id, event_id, session):
    recurring_events = mongoApi.get_recurring_events(user_id, session=session)
    if not recurring_events:
        return None

    for event in recurring_events:
        if event['_id'] == event_id:
            return event

    return None


def get_recurring_task(user_id, task_id, session):
    recurring_tasks = mongoApi.get_recurring_tasks(user_id, session=session)
    if not recurring_tasks:
        return None

    recurring_tasks = recurring_tasks['recurring_tasks']
    for task in recurring_tasks:
        if task['_id'] == task_id:
            return task

    return None


def get_task(user_id, task_id, session):
    tasks = mongoApi.get_task_list(user_id, session=session)
    if not tasks:
        return None

    tasks = tasks['task_list']
    for task in tasks:
        if task['_id'] == task_id:
            return task

    return None


def add_task_and_automate(user_id, task_data, session):
    task = dict_to_entities.create_new_task(user_id, task_data, session=session)
    if not task or not task.duration:
        return None, None

    end_time = datetime.today() + timedelta(days=7)
    if task.frequency == "Once" or task.frequency is None:
        if not mongoApi.add_task(user_id, task, session=session):
            return None, None

        end_time = task.deadline if task.deadline is not None and task.deadline < end_time else end_time
        return task, end_time
    else:
        current_date = datetime(year=datetime.now().year, month=datetime.now().month, day=datetime.now().day)
        deadline = find_deadline_for_next_recurring_task(task, current_date)
        task_instance = task.generate_recurring_instance(deadline)
        task.previous_done = deadline
        if not mongoApi.add_recurring_task(user_id, task, session=session):
            return None, None

        end_time = deadline if deadline < end_time else end_time
        task_instance.status = 'active'
        return task_instance, end_time
