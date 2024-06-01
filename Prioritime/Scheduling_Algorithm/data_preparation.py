from enum import Enum

from datetime import datetime, time, timedelta
from Prioritime.Model_Logic import user_preferences, calendar_objects
from Prioritime.mongoDB import mongoApi, mongo_utils


class Activity:
    def __init__(self, id, duration, free_blocks=None, deadline=None, preferred_days=None, preferred_times=None):
        self.id = id
        self.duration = duration
        self.free_blocks = free_blocks  # List of tuples (start_time, end_time)
        self.total_free_blocks = free_blocks
        self.deadline = deadline
        self.preferred_days = preferred_days  # List of weekdays (e.g., [0, 2, 4])
        self.preferred_times = preferred_times  # List of tuples (start_time, end_time)


class DayPart(Enum):
    Morning = (time(hour=8), time(hour=12))
    Noon = (time(hour=12), time(hour=16))
    Evening = (time(hour=16), time(hour=20))


def data_preparation(user_id, task_list, begin_date, end_date):
    activities = []
    all_free_time_blocks = []
    current_date = begin_date
    general_preferences = mongoApi.find_preference(user_id, 'general')
    general_preferences = general_preferences['general']
    while current_date <= end_date:
        date = {'year': current_date.year, 'month': current_date.month, 'day': current_date.day}
        schedule = mongo_utils.get_schedule(user_id, date)

        if not schedule.day_off:
            all_free_time_blocks.append(schedule.free_time_init(
                datetime.strptime(general_preferences['start_time'], "%H:%M:%S")
                .replace(year=date['year'], month=date['month'], day=date['day']),
                datetime.strptime(general_preferences['end_time'], "%H:%M:%S")
                .replace(year=date['year'], month=date['month'], day=date['day'])))

        current_date = current_date + timedelta(days=1)

    for task in task_list:
        if task.duration:
            preference_dict = mongoApi.find_preference(user_id, task.name)
            preferred_days = None
            preferred_times = None
            if preference_dict:
                preference_dict = preference_dict[task.name]
                preference = user_preferences.Preference(**preference_dict)
                preferred_days = preference.possible_days
                preferred_times = arrange_preferred_times(preference.day_part)

            activity = Activity(
                id=task.id(),
                duration=task.duration,
                deadline=task.deadline,
                preferred_days=preferred_days,
                preferred_times=preferred_times,
                free_blocks=arrange_free_time_blocks(task, all_free_time_blocks)
            )
            activities.append(activity)

    return activities


def arrange_preferred_times(day_part):
    times = []
    if day_part['morning']:
        start_time, end_time = DayPart.Morning.value
        times.append((start_time, end_time))

    if day_part['noon']:
        start_time, end_time = DayPart.Noon.value
        times.append((start_time, end_time))

    if day_part['evening']:
        start_time, end_time = DayPart.Evening.value
        times.append((start_time, end_time))

    return times


def arrange_free_time_blocks(task, all_free_time_blocks):
    task_free_time_blocks = []
    for daly_blocks in all_free_time_blocks:
        for block in daly_blocks:
            start_time, end_time = block
            if start_time + timedelta(minutes=task.duration) <= end_time:
                if task.deadline is None or task.deadline >= end_time:
                    task_free_time_blocks.append((start_time, end_time))

                elif start_time + timedelta(minutes=task.duration) <= task.deadline < end_time:
                    task_free_time_blocks.append((start_time, task.deadline))

    return task_free_time_blocks


def arrange_prev_schedule(task_list):
    prev_schedule = {task.id(): task for task in task_list}
    return prev_schedule
