from . import mongoApi
from Prioritime.Model_Logic import dict_to_entities, dict_to_entities_from_requests, calendar_objects
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


# Function to get the monthly calendar with recurring events placed
def get_monthly_calendar(user_id, date, session):
    month = date.month
    year = date.year
    # Loading the monthly calendar from the DB
    monthly_calendar_dict = mongoApi.get_monthly_calendar(user_id, date, session=session)
    # If exists make it an object if not create a new one
    if monthly_calendar_dict:
        monthly_calendar = dict_to_entities.dict_to_monthly_calendar(monthly_calendar_dict)
    else:
        monthly_calendar = create_new_month(year, month)

    # Load the recurring events list from the DB
    recurring_events = mongoApi.get_recurring_events(user_id, session=session)
    if not recurring_events:
        return monthly_calendar

    # Adding the recurring events instances in the correct schedules
    for schedule in monthly_calendar.list_of_schedules:
        datetime_date = datetime(year=year, month=month, day=schedule.date)
        insert_recurring_events_to_schedule(recurring_events, schedule, datetime_date)

    return monthly_calendar


# Function to get the daily schedule with recurring events placed
def get_schedule(user_id, date, session):
    year = date.year
    month = date.month
    day = date.day
    # Loading the schedule from the DB
    schedule_dict = mongoApi.get_schedule(user_id, date, session=session)
    # If exists make it an object if not create a new one
    if schedule_dict:
        schedule = dict_to_entities.dict_to_schedule(schedule_dict)
    else:
        schedule = create_new_schedule(year, month, day)

    # Loading the recurring events list from the DB
    recurring_events = mongoApi.get_recurring_events(user_id, session=session)
    if not recurring_events:
        return schedule

    # Inserting the necessary recurring events to the schedule
    insert_recurring_events_to_schedule(recurring_events, schedule, date)

    return schedule


# Function to get all the schedules from a date to another date
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


# Function for inserting recurring events to a schedule
def insert_recurring_events_to_schedule(recurring_events, schedule, date):
    for recurring_event_dict in recurring_events:
        recurring_event = dict_to_entities.dict_to_event(recurring_event_dict)
        if is_recurring_on_date(recurring_event, date):
            recurring_event.start_time = recurring_event.start_time.replace(year=date.year, month=date.month,
                                                                            day=date.day)
            recurring_event.end_time = recurring_event.end_time.replace(year=date.year, month=date.month, day=date.day)
            schedule.add_event(recurring_event)


# Function for checking if recurring event has instance in a specific date
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


# Function for handling event updates
def update_event(user_id, old_date, new_date, event_id, updated_data, session):
    item_type = updated_data.get('item_type')
    if item_type == 'recurring event':
        # If it's a recurring event changed to normal,
        # removing from the recurring event list and adding the updated event to the calendar
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
            # Updating fields of the recurring event
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


# Updating task and recurring task in the DB
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


# Function to get the task list with the recurring tasks instances
def get_task_list(user_id, deadline=None, session=None):
    # Adding recurring tasks instances if needed
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


# Function to insert recurring tasks instances if needed
def insert_recurring_tasks_to_task_list(user_id, session):
    recurring_tasks_dict = mongoApi.get_recurring_tasks(user_id, session=session)
    if recurring_tasks_dict is None:
        return False

    recurring_tasks_dict = recurring_tasks_dict['recurring_tasks']
    if not recurring_tasks_dict:
        return True

    current_date = datetime.now()
    recurring_tasks = dict_to_entities.dict_to_task_list(recurring_tasks_dict)
    for recurring_task in recurring_tasks.list_of_tasks:
        if recurring_task.previous_done is None or recurring_task.previous_done < current_date:
            if recurring_task.last_instance:
                mongoApi.delete_task(user_id=user_id, task_id=recurring_task.last_instance, session=session)

            # checking if recurring task deadline passed, so it would stop creating new tasks and be deleted
            if recurring_task.deadline and current_date > recurring_task.deadline:
                if mongoApi.delete_recurring_task(user_id=user_id, task_id=recurring_task.id(), session=session):
                    return True
                else:
                    return False

            deadline = find_deadline_for_next_recurring_task(recurring_task, current_date)

            # checking if recurring task deadline is after the calculated deadline, so it would stop creating new tasks
            if recurring_task.deadline and deadline > recurring_task.deadline:
                deadline = recurring_task.deadline

            new_task = recurring_task.generate_recurring_instance(deadline)
            if mongoApi.add_task(user_id, new_task, session=session):
                update_recurring_task = {'previous_done': deadline.isoformat(),
                                         'last_instance': recurring_task.last_instance}
                if not mongoApi.update_recurring_task(user_id, recurring_task.id(), update_recurring_task,
                                                      session=session):
                    return False
            else:
                return False

    return True


# Function to calculate the deadline for a recurring task instance
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


# Function to get a specific recurring event by id
def get_recurring_event(user_id, event_id, session):
    recurring_events = mongoApi.get_recurring_events(user_id, session=session)
    if not recurring_events:
        return None

    for event in recurring_events:
        if event['_id'] == event_id:
            return event

    return None


# Function to get a specific recurring task by id
def get_recurring_task(user_id, task_id, session):
    recurring_tasks = mongoApi.get_recurring_tasks(user_id, session=session)
    if not recurring_tasks:
        return None

    recurring_tasks = recurring_tasks['recurring_tasks']
    for task in recurring_tasks:
        if task['_id'] == task_id:
            return task

    return None


# Function to find a specific task from the task list
def get_task(user_id, task_id, session):
    tasks = mongoApi.get_task_list(user_id, session=session)
    if not tasks:
        return None

    tasks = tasks['task_list']
    for task in tasks:
        if task['_id'] == task_id:
            return task

    return None


# Function for save and automate task create the tasks needed and return it with the end date for the schedule algorithm
def add_task_and_automate(user_id, task_data, session):
    task = dict_to_entities_from_requests.create_new_task(user_id, task_data, session=session)
    current_date = datetime.now()
    if not task or not task.duration or (task.deadline and task.deadline < current_date):
        return None, None

    end_time = datetime.today() + timedelta(days=7)
    if task.frequency == "Once" or task.frequency is None:
        end_time = task.deadline if task.deadline is not None and task.deadline < end_time else end_time
        task.status = "active"
        return task, end_time

    else:
        deadline = find_deadline_for_next_recurring_task(task, current_date)
        if task.deadline and deadline > task.deadline:
            deadline = task.deadline

        task_instance = task.generate_recurring_instance(deadline)
        task.previous_done = deadline
        if not mongoApi.add_recurring_task(user_id, task, session=session):
            return None, None

        end_time = deadline if deadline < end_time else end_time
        task_instance.status = 'active'
        return task_instance, end_time
