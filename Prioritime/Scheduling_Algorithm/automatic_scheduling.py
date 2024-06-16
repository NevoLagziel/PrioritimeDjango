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


def schedule_single_task(user_id, task, start_date, end_date, session):
    task_list = [task]  # in a list just so the algorithm could handle it
    activity = data_preparation.data_preparation(user_id, task_list, start_date, end_date, session=session)
    if len(activity) == 0:
        return False
    best_plan, unscheduled_activities = swo_algorithm.schedule_activities(activity)
    print(best_plan, unscheduled_activities)
    if update_tasks(user_id, task_list, best_plan, session=session):
        return True

    return False


def schedule_tasks(user_id, list_of_task_ids, start_date, end_date, session):
    task_list_dict = mongo_utils.get_task_list(user_id, session=session)
    if task_list_dict is None:
        return False
    task_list = dict_to_entities.dict_to_task_list(task_list_dict['task_list'])
    filtered_task_list = task_list.filter_by(id_list=list_of_task_ids)
    if filtered_task_list is None or len(filtered_task_list) == 0:
        return False

    activities = data_preparation.data_preparation(user_id, filtered_task_list, start_date, end_date, session=session)
    if len(activities) == 0:
        return False

    best_plan, unscheduled_activities = swo_algorithm.schedule_activities(activities=activities)

    if update_tasks(user_id, filtered_task_list, best_plan, session=session):
        return True

    return False


# def re_schedule_tasks_2(user_id, date, session):
#     task_list_dict = mongo_utils.get_task_list(user_id, session=session)
#     if task_list_dict is None:
#         return False
#
#     task_list = dict_to_entities.dict_to_task_list(task_list_dict['task_list'])
#     if date['day'] is not None:
#         start_date = end_date = datetime(year=date['year'], month=date['month'], day=date['day'])
#     else:
#         start_date, end_date = get_first_and_last_date_of_month(date['year'], date['month'])
#
#     filtered_task_list = task_list.filter_by_date(start_date, end_date)
#     if filtered_task_list is None or len(filtered_task_list) == 0:
#         return False
#
#     activities = data_preparation.data_preparation(user_id, filtered_task_list, start_date, end_date, session=session)
#     if len(activities) == 0:
#         return False
#
#     prev_schedule = data_preparation.arrange_prev_schedule(filtered_task_list)
#     best_plan, unscheduled_activities = swo_algorithm.schedule_activities(activities=activities, prev_schedule=prev_schedule)
#
#     if update_tasks_2(user_id, filtered_task_list, best_plan, session=session):
#         return True
#
#     return False


# instead of leaving the tasks in the list, placing them in the calendar
# def re_schedule_tasks_3(user_id, date, session):
#     if date['day'] is not None:
#         start_date = end_date = datetime(year=date['year'], month=date['month'], day=date['day'])
#     else:
#         start_date, end_date = get_first_and_last_date_of_month(date['year'], date['month'])
#
#     task_list = remove_all_scheduled_tasks_from_schedule(user_id, start_date, end_date, session=session)
#     if task_list is None or len(task_list) == 0:
#         return False
#
#     activities = data_preparation.data_preparation_3(user_id, task_list, start_date, end_date, session=session)
#     if len(activities) == 0:
#         return False
#
#     prev_schedule = data_preparation.arrange_prev_schedule(task_list)
#     best_plan, unscheduled_activities = swo_algorithm.schedule_activities(activities=activities,
#                                                                           prev_schedule=prev_schedule)
#     print(best_plan, unscheduled_activities)
#     if update_tasks(user_id, task_list, best_plan, session=session):
#         return True
#
#     return False


# Version where you update the schedules only at the end
# And transfer the loaded schedules for efficiency
def re_schedule_tasks(user_id, date, session):
    if date['day'] is not None:
        start_date = end_date = datetime(year=date['year'], month=date['month'], day=date['day'])
    else:
        start_date, end_date = get_first_and_last_date_of_month(date['year'], date['month'])

    task_list, schedules = remove_all_scheduled_tasks_from_schedule(user_id, start_date, end_date, session=session)
    if task_list is None or len(task_list) == 0:
        return False

    activities = data_preparation.data_preparation(user_id, task_list, start_date, end_date, session=session, schedules=schedules)
    if len(activities) == 0:
        return False

    print('here')
    prev_schedule = data_preparation.arrange_prev_schedule(task_list)
    best_plan, unscheduled_activities = swo_algorithm.schedule_activities(activities=activities, prev_schedule=prev_schedule)
    print(best_plan, unscheduled_activities)
    if update_tasks(user_id, task_list, best_plan, session=session):
        return True

    return False


# def remove_all_scheduled_tasks_from_schedule_3(user_id, start_date, end_date, session):
#     task_list = []
#     current_date = start_date
#     while current_date <= end_date:
#         schedule = mongo_utils.get_schedule(user_id, current_date, session=session)
#         if schedule is None:
#             return None
#
#         tasks_removed = 0
#         for event in schedule.event_list:
#             if event.item_type == 'task':
#                 schedule.event_list.remove(event)
#                 task_list.append(event)
#                 tasks_removed += 1
#
#         if tasks_removed > 0:
#             if not mongoApi.update_schedule(user_id, current_date, schedule, session=session):
#                 return None
#
#         current_date = current_date + timedelta(days=1)
#
#     return task_list


def remove_all_scheduled_tasks_from_schedule(user_id, start_date, end_date, session):
    task_list = []
    schedules = []
    current_date = start_date
    while current_date <= end_date:
        schedule = mongo_utils.get_schedule(user_id, current_date, session=session)
        if schedule is None:
            return None, None

        tasks_removed = 0
        for event in schedule.event_list:
            if event.item_type == 'task':
                schedule.event_list.remove(event)
                task_list.append(event)
                tasks_removed += 1

        schedules.append(schedule)
        current_date = current_date + timedelta(days=1)

    return task_list, schedules


# updating the tasks in the calendar and not in the task list
# def update_tasks_3(user_id, task_list, best_plan, session):
#     for task in task_list:
#         if best_plan[task.id()] is not None:
#             start_time, end_time = best_plan[task.id()]
#         else:
#             start_time, end_time = None, None
#
#         was_scheduled = False if task.status == 'pending' else True
#         task.schedule(start_time=start_time, end_time=end_time)
#         if start_time is not None and end_time is not None:
#             if not was_scheduled:
#                 if not mongoApi.delete_task(user_id, task.id(), session=session):
#                     return False
#             if not mongoApi.add_event(user_id, task, start_time, session=session):
#                 return False
#         else:
#             if was_scheduled:
#                 if not mongoApi.add_task(user_id, task, session=session):
#                     return False
#
#     return True
#
#
# # need to check what happened if the task did not get scheduled !!!
# def update_tasks_2(user_id, task_list, best_plan, session):
#     for task in task_list:
#         if best_plan[task.id()] is not None:
#             start_time, end_time = best_plan[task.id()]
#         else:
#             start_time, end_time = None, None
#
#         task.schedule(start_time=start_time, end_time=end_time)
#         if not mongoApi.update_task(user_id, task.id(), task.__dict__(), session=session):
#             return False  # not sure about that because it could succeed but change nothing
#
#     return True


# Version for handling the delete of tasks from the schedule here and not in the update schedule
# Fixes the increment problem while making us transfer the already loaded schedules instead of updating them
# and then loading them all over again
def update_tasks(user_id, task_list, best_plan, session):
    for task in task_list:
        if best_plan[task.id()] is not None:
            start_time, end_time = best_plan[task.id()]
        else:
            start_time, end_time = None, None

        was_scheduled = True if task.status == 'scheduled' else False
        old_date = task.start_time
        task.schedule(start_time=start_time, end_time=end_time)
        if was_scheduled:
            if not mongoApi.delete_event(user_id, old_date, task.id(), session=session):
                return False

        if start_time is not None and end_time is not None:
            if not was_scheduled:
                if not mongoApi.delete_task(user_id, task.id(), session=session):
                    return False

            if not mongoApi.add_event(user_id, task, start_time, session=session):
                return False

        else:
            if was_scheduled:
                if not mongoApi.add_task(user_id, task, session=session):
                    return False

    return True
