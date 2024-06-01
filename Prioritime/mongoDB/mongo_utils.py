from . import mongoApi
from Prioritime.Model_Logic import dict_to_entities, calendar_objects
import calendar
from datetime import datetime, timedelta
from datetime import date as date_lib


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
        starting_day=calendar.monthrange(year, month)[0],
        list_of_schedules=list_of_schedules
    )
    return monthly_calendar


def create_new_schedule(year, month, day):
    schedule = calendar_objects.Schedule(
        date=day,
        day=(calendar.weekday(year, month, day) + 1),
    )
    return schedule


def get_monthly_calendar(user_id, date):
    month = int(date['month'])
    year = int(date['year'])
    monthly_calendar_dict = mongoApi.get_monthly_calendar(user_id, date)
    if monthly_calendar_dict:
        monthly_calendar = dict_to_entities.dict_to_monthly_calendar(monthly_calendar_dict)
    else:
        monthly_calendar = create_new_month(year, month)

    recurring_events = mongoApi.get_recurring_events(user_id)
    task_list_dict = get_task_list(user_id)

    if not recurring_events and not task_list_dict:
        return monthly_calendar

    tasks = dict_to_entities.dict_to_task_list(task_list_dict) if task_list_dict is not None else None
    for schedule in monthly_calendar.list_of_schedules:
        datetime_date = date_lib(year=year, month=month, day=schedule.date)
        if recurring_events:
            insert_recurring_events_to_schedule(recurring_events, schedule, datetime_date)

        # remove that if updating the tasks to be in a schedule
        if tasks:
            insert_scheduled_tasks_to_schedule(tasks, schedule, datetime_date)

    return monthly_calendar


def get_schedule(user_id, date):
    day = int(date['day'])
    month = int(date['month'])
    year = int(date['year'])
    datetime_date = datetime(year=year, month=month, day=day)
    schedule_dict = mongoApi.get_schedule(user_id, date)
    if schedule_dict:
        schedule = dict_to_entities.dict_to_schedule(schedule_dict)
    else:
        schedule = create_new_schedule(year, month, day)

    recurring_events = mongoApi.get_recurring_events(user_id)
    if recurring_events:
        insert_recurring_events_to_schedule(recurring_events, schedule, datetime_date)

    # remove that if updating the tasks to be in a schedule
    task_list_dict = get_task_list(user_id)
    if task_list_dict:
        tasks = dict_to_entities.dict_to_task_list(task_list_dict['task_list'])
        insert_scheduled_tasks_to_schedule(tasks, schedule, datetime_date)

    return schedule


def insert_recurring_events_to_schedule(recurring_events, schedule, date):
    for recurring_event_dict in recurring_events:
        recurring_event = dict_to_entities.dict_to_event(recurring_event_dict)
        if is_recurring_on_date(recurring_event, date):
            recurring_event.start_time = (
                (recurring_event.start_time.replace(year=date.year, month=date.month, day=date.day)).isoformat())

            recurring_event.end_time = (
                recurring_event.end_time.replace(year=date.year, month=date.month, day=date.day)).isoformat()

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
            delta_days = (target_date - first_appearance).days
            if recurrence_pattern == 'Every Week':
                return delta_days % 7 == 0

            elif recurrence_pattern == 'Every 2 Weeks':
                return delta_days % 14 == 0

    return False


def update_event(user_id, old_date, new_date, event_id, updated_data):
    frequency = updated_data.get('frequency')
    if frequency is not None and frequency != 'Once':
        new_updated_data = updated_data.copy()
        if old_date.date() != new_date.date():
            new_updated_data['first_appearance'] = new_date.isoformat()

        if mongoApi.update_recurring_event(user_id, event_id, new_updated_data):
            return True

    elif old_date.date() == new_date.date():
        if mongoApi.update_event(user_id, event_id, old_date, updated_data):
            return True
    else:
        updated_event = dict_to_entities.create_new_event(updated_data)
        if mongoApi.delete_event(user_id, old_date, event_id):
            if mongoApi.add_event(user_id, updated_event, new_date):
                return True

    return False


def get_task_list(user_id, deadline=None):
    if not insert_recurring_tasks_to_task_list(user_id):
        return None

    task_list_dict = mongoApi.get_task_list(user_id)
    if not deadline:
        return task_list_dict

    task_list = dict_to_entities.dict_to_task_list(task_list_dict['task_list'])
    deadline = date_lib.fromisoformat(deadline)
    filtered_task_list = calendar_objects.Tasks(task_list.get_list_by_deadline(deadline))
    return filtered_task_list.__dict__()


def insert_recurring_tasks_to_task_list(user_id):
    recurring_tasks_dict = mongoApi.get_recurring_tasks(user_id)
    if not recurring_tasks_dict:
        return True

    current_date = datetime(year=datetime.now().year, month=datetime.now().month, day=datetime.now().day)
    recurring_tasks = dict_to_entities.dict_to_task_list(recurring_tasks_dict)
    for recurring_task in recurring_tasks:
        if recurring_task.previous_done is None or recurring_task.previous_done < current_date:
            deadline = find_deadline_for_next_recurring_task(recurring_task, current_date)

            new_task = recurring_task.generate_recurring_instance(deadline)
            result = mongoApi.add_task(user_id, new_task)
            if result:
                previous_done = {'previous_done': deadline.isoformat()}
                if not mongoApi.update_recurring_task(user_id, recurring_task.id(), previous_done):
                    return False

    return True


def find_deadline_for_next_recurring_task(recurring_task, current_date):
    deadline = None
    recurrence_pattern = recurring_task.frequency
    if recurrence_pattern == 'Every Day':
        deadline = current_date + timedelta(hours=23, minutes=59, seconds=59)
    elif recurrence_pattern == 'Every Week':
        week_start = current_date - timedelta(days=current_date.weekday())
        deadline = week_start + timedelta(days=6, hours=23, minutes=59, seconds=59)
    elif recurrence_pattern == 'Every 2 Weeks':
        week_start = current_date - timedelta(days=current_date.weekday())
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
