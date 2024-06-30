from Prioritime.mongoDB import mongoApi, mongo_utils
from Prioritime.Model_Logic import dict_to_entities
from datetime import datetime, timedelta
import calendar
from . import data_preparation, swo_algorithm


# Calculating the first and last day of a month for re-schedule month
def get_first_and_last_date_of_month(year, month):
    num_days_in_month = calendar.monthrange(year, month)[1]
    first_date = datetime(year, month, 1)
    last_date = datetime(year, month, num_days_in_month)
    return first_date, last_date


# Scheduling tasks from the task list by a list of id's
def schedule_tasks_by_id_list(user_id, list_of_task_ids, start_date, end_date, session):
    task_list_dict = mongo_utils.get_task_list(user_id, session=session)
    if task_list_dict is None:
        return False

    task_list = dict_to_entities.dict_to_task_list(task_list_dict['task_list'])
    filtered_task_list = task_list.filter_by(id_list=list_of_task_ids)
    if filtered_task_list is None or len(filtered_task_list) == 0:
        return False

    results = schedule_tasks(user_id, filtered_task_list, start_date, end_date, session=session)
    if not results:
        return False

    return results


# Function for scheduling, preparing the data, sending to the scheduling algorithm and updating accordingly
def schedule_tasks(user_id, task_list, start_date, end_date, session, schedules=None, prev_schedule=None):
    if start_date > end_date or end_date < datetime.today().replace(hour=0, minute=0, second=0, microsecond=0):
        return False

    activities = data_preparation.data_preparation(user_id=user_id, task_list=task_list, begin_date=start_date,
                                                   end_date=end_date, session=session, schedules=schedules)
    if len(activities) == 0:
        return False

    best_plan, unscheduled_activities = swo_algorithm.schedule_activities(activities=activities,
                                                                          prev_schedule=prev_schedule)
    if best_plan is None:
        return False
    print(best_plan, unscheduled_activities)

    result = update_tasks(user_id, task_list, best_plan, session=session)
    if not result:
        return False

    return result


# Function for rescheduling tasks scheduled in a day or a month
def re_schedule_tasks(user_id, session, month=None, date=None):
    if date is not None:
        start_date = end_date = date
    elif month is not None:
        start_date, end_date = get_first_and_last_date_of_month(month.year, month.month)
    else:
        return False

    task_list, schedules = remove_all_scheduled_tasks_from_schedule(user_id, start_date, end_date, session=session)
    if task_list is None or len(task_list) == 0:
        return False

    prev_schedule = data_preparation.arrange_prev_schedule(task_list)
    results = schedule_tasks(user_id, task_list, start_date, end_date, session=session, schedules=schedules,
                             prev_schedule=prev_schedule)
    if not results:
        return False

    return results


# Function for removing the scheduled tasks from the schedules for re-scheduling process
def remove_all_scheduled_tasks_from_schedule(user_id, start_date, end_date, session):
    task_list = []
    schedules = []
    current_date = start_date
    while current_date <= end_date:
        schedule = mongo_utils.get_schedule(user_id, current_date, session=session)
        if schedule is None:
            return None, None

        tasks_removed = 0
        event_list = schedule.event_list.copy()
        for event in event_list:
            if event.item_type == 'task':
                schedule.event_list.remove(event)
                task_list.append(event)
                tasks_removed += 1

        schedules.append(schedule)
        current_date = current_date + timedelta(days=1)

    return task_list, schedules


# Function for updating the tasks after the algorithm in the DB, scheduled tasks to the calendar and not schedule to the task list
def update_tasks(user_id, task_list, best_plan, session):
    presenting_scheduled_tasks = []
    keys = best_plan.keys()
    for task in task_list:
        if task.id() in keys and best_plan[task.id()] is not None:
            start_time, end_time = best_plan[task.id()]
        else:
            start_time, end_time = None, None

        presenting_scheduled_tasks.append({'name': task.name, 'start_time': start_time})

        result = False
        if task.status == 'scheduled':
            result = update_scheduled_task(user_id, task, start_time, end_time, session=session)
        elif task.status == 'pending':
            result = update_pending_task(user_id, task, start_time, end_time, session=session)
        elif task.status == 'active':
            result = update_new_task(user_id, task, start_time, end_time, session=session)

        if not result:
            return False

    return presenting_scheduled_tasks


# Handling the update for tasks that were scheduled before
def update_scheduled_task(user_id, task, start_time, end_time, session):
    old_date = task.start_time
    if not mongoApi.delete_event(user_id, old_date, task.id(), session=session):
        return False

    task.schedule(start_time=start_time, end_time=end_time)
    if task.status == 'scheduled':
        if not mongoApi.add_event(user_id, task, start_time, session=session):
            return False

    else:
        if not mongoApi.add_task(user_id, task, session=session):
            return False

    return True


# Handling the update for tasks that were in the task list before
def update_pending_task(user_id, task, start_time, end_time, session):
    task.schedule(start_time=start_time, end_time=end_time)
    if task.status == 'scheduled':
        if not mongoApi.delete_task(user_id, task.id(), session=session):
            return False

        if not mongoApi.add_event(user_id, task, start_time, session=session):
            return False

    return True


# Handling the update for a new task (save and automate)
def update_new_task(user_id, task, start_time, end_time, session):
    task.schedule(start_time=start_time, end_time=end_time)
    if task.status == 'scheduled':
        if mongoApi.add_event(user_id, task, start_time, session=session):
            return True

    return False
