from Prioritime.Model_Logic import calendar_objects
from Prioritime.mongoDB import mongoApi, mongo_utils
from Prioritime.Model_Logic import dict_to_entities
from datetime import datetime, timedelta
import calendar
from . import data_preparation, swo_algorithm


def get_first_and_last_date_of_month(year, month):
    num_days_in_month = calendar.monthrange(year, month)[1]
    first_date = datetime(year, month, 1)
    last_date = datetime(year, month, num_days_in_month)
    return first_date, last_date


def schedule_single_task(user_id, task, start_date, end_date):
    task_list = [task]  # in a list just so the algorithm could handle it
    activity = data_preparation.data_preparation(user_id, task_list, start_date, end_date)
    best_plan, unscheduled_activities = swo_algorithm.schedule_activities(activity)
    if len(unscheduled_activities) > 0:
        return False
    else:
        update_tasks(user_id, task_list, best_plan)
        return True


def schedule_tasks(user_id, list_of_task_ids, start_date, end_date):
    task_list_dict = mongo_utils.get_task_list(user_id)
    task_list = dict_to_entities.dict_to_task_list(task_list_dict['task_list'])
    filtered_task_list = task_list.filter_by_ids(list_of_task_ids)

    activities = data_preparation.data_preparation(user_id, filtered_task_list, start_date, end_date)
    best_plan, unscheduled_activities = swo_algorithm.schedule_activities(activities)

    update_tasks(user_id, filtered_task_list, best_plan)
    return task_list, unscheduled_activities


def re_schedule_tasks(user_id, date):
    task_list_dict = mongo_utils.get_task_list(user_id)
    task_list = dict_to_entities.dict_to_task_list(task_list_dict['task_list'])
    if date['day'] is not None:
        start_date = end_date = datetime(year=date['year'], month=date['month'], day=date['day'])
    else:
        start_date, end_date = get_first_and_last_date_of_month(date['year'], date['month'])

    filtered_task_list = task_list.filter_by_date(start_date, end_date)
    activities = data_preparation.data_preparation(user_id, filtered_task_list, start_date, end_date)

    prev_schedule = data_preparation.arrange_prev_schedule(filtered_task_list)
    best_plan, unscheduled_activities = swo_algorithm.schedule_activities(activities, prev_schedule)

    update_tasks(user_id, filtered_task_list, best_plan)
    return task_list, unscheduled_activities


# instead of leaving the tasks in the list, placing them in the calendar
def re_schedule_tasks_2(user_id, date):
    if date['day'] is not None:
        start_date = end_date = datetime(year=date['year'], month=date['month'], day=date['day'])
    else:
        start_date, end_date = get_first_and_last_date_of_month(date['year'], date['month'])

    task_list = remove_all_scheduled_tasks_from_schedule(user_id, start_date, end_date)
    activities = data_preparation.data_preparation(user_id, task_list, start_date, end_date)

    prev_schedule = data_preparation.arrange_prev_schedule(task_list)
    best_plan, unscheduled_activities = swo_algorithm.schedule_activities(activities, prev_schedule)

    update_tasks_2(user_id, task_list, best_plan)
    return task_list, unscheduled_activities


# for re_schedule_tasks_2
def remove_all_scheduled_tasks_from_schedule(user_id, start_date, end_date):
    task_list = []
    current_date = start_date
    while current_date <= end_date:
        schedule = mongo_utils.get_schedule(user_id, current_date)
        for event in schedule.event_list:
            if event['type'] == 'task':
                task = schedule.event_list.pop(event)
                task_list.append(task)

        mongoApi.update_schedule(user_id, current_date, schedule)
        current_date = current_date + timedelta(days=1)

    return task_list


# updating the tasks in the calendar and not in the task list
def update_tasks_2(user_id, task_list, best_plan):
    for task in task_list:
        start_time, end_time = best_plan[task.id()]
        was_scheduled = False if task.status == 'pending' else True
        task.schedule(start_time=start_time, end_time=end_time)
        if start_time is not None and end_time is not None:
            if not was_scheduled:
                mongoApi.delete_task(user_id, task.id())
            mongoApi.add_event(user_id, task, start_time)
        else:
            if was_scheduled:
                mongoApi.add_task(user_id, task)


# need to check what happened if the task did not get scheduled !!!
def update_tasks(user_id, task_list, best_plan):
    for task in task_list:
        start_time, end_time = best_plan[task.id()]
        task.schedule(start_time=start_time, end_time=end_time)
        mongoApi.update_task(user_id, task.id(), task.__dict__())
