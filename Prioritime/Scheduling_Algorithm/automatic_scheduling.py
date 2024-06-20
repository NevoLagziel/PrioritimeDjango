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


def schedule_single_task(user_id, task, start_date, end_date, session):
    task_list = [task]  # in a list just so the algorithm could handle it
    activity = data_preparation.data_preparation(user_id, task_list, start_date, end_date, session=session)
    if len(activity) == 0:
        return False

    best_plan, unscheduled_activities = swo_algorithm.schedule_activities(activity)
    if best_plan is None:
        return False

    print(best_plan, unscheduled_activities)
    if not update_tasks(user_id, task_list, best_plan, session=session):
        return False

    return True


def schedule_tasks_by_id_list(user_id, list_of_task_ids, start_date, end_date, session):
    task_list_dict = mongo_utils.get_task_list(user_id, session=session)
    if task_list_dict is None:
        return False

    task_list = dict_to_entities.dict_to_task_list(task_list_dict['task_list'])
    filtered_task_list = task_list.filter_by(id_list=list_of_task_ids)
    if filtered_task_list is None or len(filtered_task_list) == 0:
        return False

    if not schedule_tasks(user_id, filtered_task_list, start_date, end_date, session=session):
        return False

    return True


def schedule_tasks(user_id, task_list, start_date, end_date, session, schedules=None, prev_schedule=None):
    if start_date > end_date or end_date < datetime.today().replace(hour=0, minute=0, second=0, microsecond=0):
        return False

    activities = data_preparation.data_preparation(user_id=user_id, task_list=task_list, begin_date=start_date, end_date=end_date, session=session, schedules=schedules)
    if len(activities) == 0:
        return False

    print(activities)
    best_plan, unscheduled_activities = swo_algorithm.schedule_activities(activities=activities, prev_schedule=prev_schedule)
    if best_plan is None:
        return False

    if not update_tasks(user_id, task_list, best_plan, session=session):
        return False

    return True

# FIXME scheduling tasks by id list function
# def schedule_tasks(user_id, list_of_task_ids, start_date, end_date, session):
#     task_list_dict = mongo_utils.get_task_list(user_id, session=session)
#     if task_list_dict is None:
#         return False
#
#     task_list = dict_to_entities.dict_to_task_list(task_list_dict['task_list'])
#     filtered_task_list = task_list.filter_by(id_list=list_of_task_ids)
#     if filtered_task_list is None or len(filtered_task_list) == 0:
#         return False
#
#     activities = data_preparation.data_preparation(user_id=user_id, task_list=filtered_task_list, begin_date=start_date,
#                                                    end_date=end_date, session=session)
#     if len(activities) == 0:
#         return False
#
#     best_plan, unscheduled_activities = swo_algorithm.schedule_activities(activities=activities)
#     if best_plan is None:
#         return False
#
#     if update_tasks(user_id, filtered_task_list, best_plan, session=session):
#         return True
#
#     return False


# def re_schedule_tasks(user_id, date, session):
#     if date['day'] is not None:
#         start_date = end_date = datetime(year=date['year'], month=date['month'], day=date['day'])
#     else:
#         start_date, end_date = get_first_and_last_date_of_month(date['year'], date['month'])
#
#     task_list, schedules = remove_all_scheduled_tasks_from_schedule(user_id, start_date, end_date, session=session)
#     if task_list is None or len(task_list) == 0:
#         return False
#
#     activities = data_preparation.data_preparation(user_id, task_list, start_date, end_date, session=session,
#                                                    schedules=schedules)
#     if len(activities) == 0:
#         return False
#
#     prev_schedule = data_preparation.arrange_prev_schedule(task_list)
#     best_plan, unscheduled_activities = swo_algorithm.schedule_activities(activities=activities,
#                                                                           prev_schedule=prev_schedule)
#     if best_plan is None:
#         return False
#
#     print(best_plan, unscheduled_activities)
#     if update_tasks(user_id, task_list, best_plan, session=session):
#         return True
#
#     return False

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
    if not schedule_tasks(user_id, task_list, start_date, end_date, session=session, schedules=schedules, prev_schedule=prev_schedule):
        return False

    return True


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


# FIXME the working function for updating
# def update_tasks(user_id, task_list, best_plan, session):
#     for task in task_list:
#         if best_plan[task.id()] is not None:
#             start_time, end_time = best_plan[task.id()]
#         else:
#             start_time, end_time = None, None
#
#         was_scheduled = True if task.status == 'scheduled' else False
#         old_date = task.start_time
#         task.schedule(start_time=start_time, end_time=end_time)
#         if was_scheduled:
#             if not mongoApi.delete_event(user_id, old_date, task.id(), session=session):
#                 return False
#
#         if task.status == 'scheduled':
#             if not was_scheduled:
#                 if not mongoApi.delete_task(user_id, task.id(), session=session):
#                     return False
#
#             if not mongoApi.add_event(user_id, task, start_time, session=session):
#                 return False
#
#         else:
#             if was_scheduled:
#                 if not mongoApi.add_task(user_id, task, session=session):
#                     return False
#
#     return True

def update_tasks(user_id, task_list, best_plan, session):
    for task in task_list:
        if best_plan[task.id()] is not None:
            start_time, end_time = best_plan[task.id()]
        else:
            start_time, end_time = None, None

        result = False
        if task.status == 'scheduled':
            result = update_scheduled_task(user_id, task, start_time, end_time, session=session)
        elif task.status == 'pending':
            result = update_pending_task(user_id, task, start_time, end_time, session=session)
        elif task.status == 'new':
            result = update_new_task(user_id, task, start_time, end_time, session=session)

        if not result:
            return False

    return True


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


def update_pending_task(user_id, task, start_time, end_time, session):
    task.schedule(start_time=start_time, end_time=end_time)
    if task.status == 'scheduled':
        if not mongoApi.delete_task(user_id, task.id(), session=session):
            return False

        if not mongoApi.add_event(user_id, task, start_time, session=session):
            return False

    return True


def update_new_task(user_id, task, start_time, end_time, session):
    task.schedule(start_time=start_time, end_time=end_time)
    if task.status == 'scheduled':
        if not mongoApi.add_event(user_id, task, start_time, session=session):
            return False

    else:
        if not mongoApi.add_task(user_id, task, session=session):
            return False

    return True
